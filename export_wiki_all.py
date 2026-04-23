#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书Wiki知识库批量导出工具
递归导出父页面下的所有子页面内容
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json
import time
import os
import re

APP_ID = "cli_a962856f89bbdcd2"
APP_SECRET = "5WcPt6Cmz53Xg8qBPRtlMDUHWiscduAg"
SPACE_ID = "7619634535205997787"

class WikiExporter:
    def __init__(self, app_id, app_secret, space_id, output_dir):
        self.app_id = app_id
        self.app_secret = app_secret
        self.space_id = space_id
        self.output_dir = output_dir
        self.token = None
        self.base_url = "https://open.feishu.cn/open-apis"

    def get_token(self):
        if self.token:
            return self.token
        resp = requests.post(f"{self.base_url}/auth/v3/tenant_access_token/internal",
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={"app_id": self.app_id, "app_secret": self.app_secret})
        result = resp.json()
        self.token = result["tenant_access_token"]
        return self.token

    def headers(self):
        return {"Authorization": f"Bearer {self.get_token()}"}

    def get_node_info(self, node_token):
        """获取节点信息"""
        r = requests.get(f"{self.base_url}/wiki/v2/spaces/get_node?token={node_token}",
            headers=self.headers())
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 0:
                return data["data"]["node"]
        return None

    def get_child_nodes(self, parent_node_token):
        """获取所有子节点"""
        all_nodes = []
        page_token = None

        while True:
            params = {"parent_node_token": parent_node_token, "page_size": 50}
            if page_token:
                params["page_token"] = page_token

            r = requests.get(f"{self.base_url}/wiki/v2/spaces/{self.space_id}/nodes",
                headers=self.headers(), params=params)

            if r.status_code != 200:
                break

            data = r.json()
            if data.get("code") != 0:
                break

            items = data["data"].get("items", [])
            all_nodes.extend(items)

            if not data["data"].get("has_more", False):
                break
            page_token = data["data"].get("page_token")

        return all_nodes

    def get_block_children(self, doc_token, block_id):
        """递归获取块的所有子块内容"""
        url = f"{self.base_url}/docx/v1/documents/{doc_token}/blocks/{block_id}/children"
        all_text = []
        page_token = None

        while True:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token

            r = requests.get(url, headers=self.headers(), params=params)
            if r.status_code != 200:
                break

            data = r.json()
            if data.get("code") != 0:
                break

            items = data.get("data", {}).get("items", [])
            for item in items:
                text = self.extract_block_text(item)
                if text:
                    prefix = self.get_block_prefix(item.get("block_type"))
                    all_text.append(f"{prefix}{text}\n")

                # 递归获取子块
                children = self.get_block_children(doc_token, item["block_id"])
                if children:
                    all_text.append(children)

            if not data.get("data", {}).get("has_more", False):
                break
            page_token = data["data"].get("page_token")

        return "\n".join(all_text)

    def get_block_prefix(self, block_type):
        """根据块类型获取markdown前缀"""
        prefixes = {
            1: "# ", 2: "", 3: "# ", 4: "## ", 5: "### ",
            9: "#### ", 10: "##### ", 11: "###### ",
            12: "1. ", 13: "- ", 14: "- [ ] ", 15: "- [x] ",
            17: "> ", 22: "```\n", 24: "---\n",
        }
        return prefixes.get(block_type, "")

    def extract_block_text(self, block):
        """从块中提取文本"""
        texts = []
        for field in ["page", "text", "heading1", "heading2", "heading3",
                       "heading4", "heading5", "heading6", "quote", "code",
                       "bullet", "ordered", "todo"]:
            field_data = block.get(field, {})
            elements = field_data.get("elements", [])
            for elem in elements:
                text_run = elem.get("text_run", {})
                content = text_run.get("content", "")
                if content:
                    texts.append(content)
        return "".join(texts)

    def get_document_content(self, doc_token):
        """获取文档完整内容"""
        # 方法1: raw_content
        r = requests.get(f"{self.base_url}/docx/v1/documents/{doc_token}/raw_content",
            headers=self.headers())
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 0:
                content = data.get("data", {}).get("content", "")
                if len(content.strip()) > 50:
                    return content

        # 方法2: 递归获取所有块内容
        print(f"    递归提取块内容...")
        r = requests.get(f"{self.base_url}/docx/v1/documents/{doc_token}/blocks",
            headers=self.headers(), params={"page_size": 500})
        if r.status_code != 200:
            return None

        data = r.json()
        if data.get("code") != 0:
            return None

        items = data.get("data", {}).get("items", [])
        all_text = []

        for item in items:
            text = self.extract_block_text(item)
            if text:
                prefix = self.get_block_prefix(item.get("block_type"))
                all_text.append(f"{prefix}{text}\n")

            children = self.get_block_children(doc_token, item["block_id"])
            if children:
                all_text.append(children)

        return "\n".join(all_text)

    def sanitize_filename(self, filename):
        """清理文件名"""
        if not filename or filename.strip() == "":
            return "untitled"
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', ' ', filename)
        return filename.strip().strip('.')

    def export_node(self, node, depth=0):
        """导出单个节点"""
        node_token = node["node_token"]
        obj_token = node["obj_token"]
        title = node.get("title", "").strip()
        if not title:
            title = f"untitled_{node_token[:8]}"

        indent = "  " * depth
        print(f"{indent}导出: {title}")

        content = self.get_document_content(obj_token)
        if not content:
            print(f"{indent}  ⚠ 无法获取内容")
            return

        # 保存文件
        safe_name = self.sanitize_filename(title)
        file_path = os.path.join(self.output_dir, f"{safe_name}.md")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(content)

        size = os.path.getsize(file_path)
        print(f"{indent}  ✓ 已保存 ({size} 字节)")

        # 递归处理子节点
        if node.get("has_child", False):
            children = self.get_child_nodes(node_token)
            for child in children:
                self.export_node(child, depth + 1)
                time.sleep(0.5)

    def export_parent_page(self, parent_node_token, subdir=None):
        """导出父页面下的所有子页面"""
        node_info = self.get_node_info(parent_node_token)
        if node_info:
            title = node_info.get("title", "root")
            print(f"父页面: {title}")
            print(f"是否有子页面: {node_info.get('has_child', False)}")
        else:
            print(f"无法获取节点信息")

        # 创建子目录
        if subdir:
            export_dir = os.path.join(self.output_dir, subdir)
            os.makedirs(export_dir, exist_ok=True)
        else:
            export_dir = self.output_dir

        children = self.get_child_nodes(parent_node_token)
        print(f"找到 {len(children)} 个子页面\n")

        for i, child in enumerate(children, 1):
            print(f"[{i}/{len(children)}] ", end="")

            # 临时切换输出目录
            orig_dir = self.output_dir
            self.output_dir = export_dir
            self.export_node(child)
            self.output_dir = orig_dir

            time.sleep(0.5)

        print(f"\n完成! 共导出 {len(children)} 个页面，保存到: {export_dir}")

def main():
    base_dir = "D:/00_cursor/02_novel/飞书导出"

    exporter = WikiExporter(APP_ID, APP_SECRET, SPACE_ID, base_dir)

    # 所有父页面
    parent_pages = [
        ("S8KIw8kS9i4RYKk4GghcwHs4n3B", "第一卷_风雪同行", "第一卷_风雪同行"),
        ("W866wUZ5RiH6oJkFYvwcFesPntg", "第二卷_江南钱庄", "第二卷_江南钱庄"),
        ("G3PjwQQDEiG7yTkWgfccqNwvnEe", "第二卷小说", "第二卷小说"),
        ("VV4dwiAcOixVBNkUhZNcW45Inve", "第一卷_废墟之上生花", "第一卷_废墟之上生花"),
        ("P6Q7wOhtUiT17ekMIbecHh6Gnld", "第二卷_风月惊变与铁马冰河", "第二卷_风月惊变与铁马冰河"),
        ("VHOJwQCeoinczPkB8yFcWYC4nzc", "第三卷_天下棋局与宫杀", "第三卷_天下棋局与宫杀"),
        ("MhrqwqUVviVMTKkHUSecQ3gunzh", "第四卷_权谋江山如画", "第四卷_权谋江山如画"),
    ]

    for token, name, subdir in parent_pages:
        print(f"\n{'='*60}")
        print(f"开始导出: {name}")
        print(f"{'='*60}")
        exporter.export_parent_page(token, subdir)
        print()

    print("所有导出完成!")

if __name__ == "__main__":
    main()
