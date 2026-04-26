import './index.css';

interface YogaCourse {
  id: number;
  name: string;
  category: string;
  description: string;
  duration: number;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  instructor: string;
  imageUrl: string;
  students: number;
  rating: number;
}

interface Category {
  id: string;
  name: string;
  icon: string;
}

const categories: Category[] = [
  { id: 'all', name: '全部课程', icon: '✨' },
  { id: 'hatha', name: '哈他瑜伽', icon: '🧘' },
  { id: 'vinyasa', name: '流瑜伽', icon: '🌊' },
  { id: 'yin', name: '阴瑜伽', icon: '🌙' },
  { id: 'ashtanga', name: '阿斯汤加', icon: '🔥' },
  { id: 'restorative', name: '恢复瑜伽', icon: '🌿' },
];

const courses: YogaCourse[] = [
  {
    id: 1,
    name: '晨间唤醒',
    category: 'hatha',
    description: '唤醒身体能量，以柔和的体式开启美好一天，适合初学者',
    duration: 30,
    difficulty: 'beginner',
    instructor: '林雅琪',
    imageUrl: 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400&h=300&fit=crop',
    students: 1256,
    rating: 4.9,
  },
  {
    id: 2,
    name: '流瑜伽 Flow',
    category: 'vinyasa',
    description: '体式串联，配合呼吸流动身心，在动态中找到专注与平静',
    duration: 45,
    difficulty: 'intermediate',
    instructor: '陈明远',
    imageUrl: 'https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=400&h=300&fit=crop',
    students: 2341,
    rating: 4.8,
  },
  {
    id: 3,
    name: '深度放松阴瑜伽',
    category: 'yin',
    description: '长时间保持体式，深入筋膜与关节，释放深层紧张与压力',
    duration: 60,
    difficulty: 'beginner',
    instructor: '王若水',
    imageUrl: 'https://images.unsplash.com/photo-1518611012118-696072aa579a?w=400&h=300&fit=crop',
    students: 1876,
    rating: 4.9,
  },
  {
    id: 4,
    name: '力量阿斯汤加',
    category: 'ashtanga',
    description: '经典序列练习，建立身体力量与耐力，适合进阶练习者',
    duration: 75,
    difficulty: 'advanced',
    instructor: '张志刚',
    imageUrl: 'https://images.unsplash.com/photo-1575052814086-f385e2e2ad1b?w=400&h=300&fit=crop',
    students: 968,
    rating: 4.7,
  },
  {
    id: 5,
    name: '肩颈修复',
    category: 'restorative',
    description: '针对现代人久坐问题，修复肩颈不适，释放上半身压力',
    duration: 25,
    difficulty: 'beginner',
    instructor: '林雅琪',
    imageUrl: 'https://images.unsplash.com/photo-1552196563-55cd4e45efb3?w=400&h=300&fit=crop',
    students: 3421,
    rating: 5.0,
  },
  {
    id: 6,
    name: '晚安睡眠瑜伽',
    category: 'yin',
    description: '轻柔的晚间练习，帮助身心放松，提升睡眠质量',
    duration: 35,
    difficulty: 'beginner',
    instructor: '王若水',
    imageUrl: 'https://images.unsplash.com/photo-1508672019048-805c876b67e2?w=400&h=300&fit=crop',
    students: 2156,
    rating: 4.9,
  },
];

function getDifficultyLabel(level: string): string {
  const labels: Record<string, string> = {
    beginner: '入门',
    intermediate: '进阶',
    advanced: '高级',
  };
  return labels[level] || level;
}

function formatDuration(minutes: number): string {
  return `${minutes}分钟`;
}

function formatNumber(num: number): string {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return num.toString();
}

function renderHeader(): string {
  return `
    <header class="bg-white/80 backdrop-blur-md sticky top-0 z-50 shadow-sm">
      <nav class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-full bg-gradient-to-br from-[#6B8E7B] to-[#8FAF9E] flex items-center justify-center text-white text-xl">
            🧘
          </div>
          <span class="font-medium text-xl text-[#2D3436] tracking-wide">身心合一</span>
        </div>
        <div class="hidden md:flex items-center gap-8">
          <a href="#" class="text-[#6B8E7B] font-medium hover:text-[#5A7D6A] transition-colors">首页</a>
          <a href="#" class="text-gray-600 hover:text-[#6B8E7B] transition-colors">课程</a>
          <a href="#" class="text-gray-600 hover:text-[#6B8E7B] transition-colors">导师</a>
          <a href="#" class="text-gray-600 hover:text-[#6B8E7B] transition-colors">关于</a>
        </div>
        <button class="btn-primary text-white px-6 py-2 rounded-full font-medium">
          开始练习
        </button>
      </nav>
    </header>
  `;
}

function renderHero(): string {
  return `
    <section class="hero-gradient relative overflow-hidden">
      <div class="absolute inset-0 opacity-10">
        <div class="absolute top-20 left-10 w-32 h-32 rounded-full bg-white/30 blur-3xl animate-float"></div>
        <div class="absolute bottom-20 right-20 w-48 h-48 rounded-full bg-white/20 blur-3xl animate-float" style="animation-delay: 1s;"></div>
      </div>
      <div class="max-w-7xl mx-auto px-6 py-24 relative">
        <div class="max-w-3xl animate-fade-in-up">
          <h1 class="font-serif text-5xl md:text-6xl font-medium text-white mb-6 leading-relaxed tracking-wide">
            在呼吸之间<br/>找到内心的平静
          </h1>
          <p class="text-xl text-white/90 mb-10 max-w-xl leading-relaxed">
            探索适合你的瑜伽课程，无论是晨间唤醒还是夜间放松，让身心在每一次练习中达到和谐统一。
          </p>
          <div class="flex flex-wrap gap-4">
            <button class="bg-white text-[#6B8E7B] px-8 py-4 rounded-full font-semibold text-lg hover:shadow-xl transition-all hover:-translate-y-1">
              浏览课程
            </button>
            <button class="border-2 border-white text-white px-8 py-4 rounded-full font-semibold text-lg hover:bg-white/10 transition-all">
              了解我们
            </button>
          </div>
        </div>
      </div>
      <div class="h-16 bg-gradient-to-b from-transparent to-[#FAFAF8]"></div>
    </section>
  `;
}

function renderStats(): string {
  return `
    <section class="max-w-7xl mx-auto px-6 -mt-8 mb-16 relative z-10">
      <div class="bg-white rounded-2xl shadow-xl p-8 grid grid-cols-2 md:grid-cols-4 gap-8">
        <div class="text-center">
          <div class="text-4xl font-bold text-[#6B8E7B] mb-2">50+</div>
          <div class="text-gray-500">精选课程</div>
        </div>
        <div class="text-center">
          <div class="text-4xl font-bold text-[#6B8E7B] mb-2">15k</div>
          <div class="text-gray-500">学员人数</div>
        </div>
        <div class="text-center">
          <div class="text-4xl font-bold text-[#6B8E7B] mb-2">12</div>
          <div class="text-gray-500">专业导师</div>
        </div>
        <div class="text-center">
          <div class="text-4xl font-bold text-[#6B8E7B] mb-2">98%</div>
          <div class="text-gray-500">好评率</div>
        </div>
      </div>
    </section>
  `;
}

function renderCategories(activeCategory: string): string {
  return `
    <section class="max-w-7xl mx-auto px-6 mb-12">
      <div class="flex flex-wrap justify-center gap-3">
        ${categories.map(cat => `
          <button 
            class="category-pill px-6 py-3 rounded-full border-2 border-[#6B8E7B] font-medium transition-all
            ${activeCategory === cat.id ? 'active bg-[#6B8E7B] text-white' : 'bg-white text-[#6B8E7B] hover:bg-[#6B8E7B]/10'}"
            data-category="${cat.id}"
          >
            <span class="mr-2">${cat.icon}</span>${cat.name}
          </button>
        `).join('')}
      </div>
    </section>
  `;
}

function renderCourseCard(course: YogaCourse): string {
  return `
    <article class="course-card bg-white rounded-2xl overflow-hidden shadow-lg cursor-pointer">
      <div class="relative overflow-hidden h-48">
        <img 
          src="${course.imageUrl}" 
          alt="${course.name}" 
          class="course-image w-full h-full object-cover"
          loading="lazy"
        />
        <div class="absolute top-4 left-4">
          <span class="badge-${course.difficulty} px-3 py-1 rounded-full text-sm font-medium">
            ${getDifficultyLabel(course.difficulty)}
          </span>
        </div>
        <div class="absolute top-4 right-4 bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full text-sm font-medium text-[#6B8E7B]">
          ⏱ ${formatDuration(course.duration)}
        </div>
      </div>
      <div class="p-6">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-sm text-[#6B8E7B] font-medium">${categories.find(c => c.id === course.category)?.name || course.category}</span>
          <span class="text-gray-300">•</span>
          <span class="text-sm text-gray-500">${course.instructor}</span>
        </div>
        <h3 class="font-medium text-lg text-[#2D3436] mb-3">${course.name}</h3>
        <p class="text-gray-600 text-sm mb-4 line-clamp-2">${course.description}</p>
        <div class="flex items-center justify-between pt-4 border-t border-gray-100">
          <div class="flex items-center gap-4 text-sm text-gray-500">
            <span class="flex items-center gap-1">
              <span>👥</span> ${formatNumber(course.students)}
            </span>
            <span class="flex items-center gap-1">
              <span>⭐</span> ${course.rating}
            </span>
          </div>
          <button class="btn-primary text-white px-5 py-2 rounded-full text-sm font-medium">
            开始学习
          </button>
        </div>
      </div>
    </article>
  `;
}

function renderCourseGrid(filteredCourses: YogaCourse[]): string {
  if (filteredCourses.length === 0) {
    return `
      <div class="text-center py-16">
        <div class="text-6xl mb-4">🧘</div>
        <h3 class="text-xl font-medium text-gray-600 mb-2">暂无相关课程</h3>
        <p class="text-gray-400">尝试选择其他课程类别</p>
      </div>
    `;
  }

  return `
    <section class="max-w-7xl mx-auto px-6 mb-20">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        ${filteredCourses.map(course => renderCourseCard(course)).join('')}
      </div>
    </section>
  `;
}

function renderFeatures(): string {
  return `
    <section class="bg-gradient-to-b from-[#FAFAF8] to-white py-20">
      <div class="max-w-7xl mx-auto px-6">
        <div class="text-center mb-16">
          <h2 class="font-serif text-3xl md:text-4xl font-medium text-[#2D3436] mb-4">为什么选择我们</h2>
          <p class="text-gray-600 text-lg max-w-2xl mx-auto">专业导师团队，科学课程体系，帮助你安全、高效地开启瑜伽之旅</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div class="text-center p-8 bg-white rounded-2xl shadow-md hover:shadow-lg transition-shadow">
            <div class="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-[#6B8E7B] to-[#8FAF9E] rounded-full flex items-center justify-center text-4xl">
              🎓
            </div>
            <h3 class="font-medium text-lg text-[#2D3436] mb-3">专业认证导师</h3>
            <p class="text-gray-600">所有导师均持有国际瑜伽联盟认证，确保教学的专业性与安全性</p>
          </div>
          <div class="text-center p-8 bg-white rounded-2xl shadow-md hover:shadow-lg transition-shadow">
            <div class="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-[#C4A77D] to-[#D4B88D] rounded-full flex items-center justify-center text-4xl">
              📋
            </div>
            <h3 class="font-medium text-lg text-[#2D3436] mb-3">个性化学习路径</h3>
            <p class="text-gray-600">根据你的身体状况和目标，智能推荐最适合的课程与练习计划</p>
          </div>
          <div class="text-center p-8 bg-white rounded-2xl shadow-md hover:shadow-lg transition-shadow">
            <div class="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-[#6B8E7B] to-[#8FAF9E] rounded-full flex items-center justify-center text-4xl">
              🌟
            </div>
            <h3 class="font-medium text-lg text-[#2D3436] mb-3">随时随地练习</h3>
            <p class="text-gray-600">支持多设备同步，碎片化时间也能高效练习，灵活安排你的瑜伽生活</p>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderFooter(): string {
  return `
    <footer class="bg-[#2D3436] text-white py-16">
      <div class="max-w-7xl mx-auto px-6">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
          <div>
            <div class="flex items-center gap-3 mb-6">
              <div class="w-10 h-10 rounded-full bg-gradient-to-br from-[#6B8E7B] to-[#8FAF9E] flex items-center justify-center text-xl">
                🧘
              </div>
              <span class="font-medium text-xl tracking-wide">身心合一</span>
            </div>
            <p class="text-gray-400 leading-relaxed">
              致力于传播瑜伽智慧，帮助更多人找到身心的平衡与和谐。
            </p>
          </div>
          <div>
            <h4 class="font-semibold mb-4">课程分类</h4>
            <ul class="space-y-2 text-gray-400">
              <li><a href="#" class="hover:text-white transition-colors">哈他瑜伽</a></li>
              <li><a href="#" class="hover:text-white transition-colors">流瑜伽</a></li>
              <li><a href="#" class="hover:text-white transition-colors">阴瑜伽</a></li>
              <li><a href="#" class="hover:text-white transition-colors">阿斯汤加</a></li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold mb-4">关于我们</h4>
            <ul class="space-y-2 text-gray-400">
              <li><a href="#" class="hover:text-white transition-colors">导师团队</a></li>
              <li><a href="#" class="hover:text-white transition-colors">课程理念</a></li>
              <li><a href="#" class="hover:text-white transition-colors">用户评价</a></li>
              <li><a href="#" class="hover:text-white transition-colors">联系我们</a></li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold mb-4">关注我们</h4>
            <div class="flex gap-4">
              <a href="#" class="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-[#6B8E7B] transition-colors">
                📱
              </a>
              <a href="#" class="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-[#6B8E7B] transition-colors">
                💬
              </a>
              <a href="#" class="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-[#6B8E7B] transition-colors">
                📧
              </a>
            </div>
          </div>
        </div>
        <div class="lotus-divider h-px mb-8"></div>
        <div class="text-center text-gray-500 text-sm">
          © 2024 身心合一 Yoga. All rights reserved.
        </div>
      </div>
    </footer>
  `;
}

class YogaApp {
  private app: HTMLElement;
  private activeCategory: string = 'all';

  constructor() {
    this.app = document.getElementById('app')!;
    this.render();
    this.setupEventListeners();
  }

  private render(): void {
    const filteredCourses = this.activeCategory === 'all'
      ? courses
      : courses.filter(c => c.category === this.activeCategory);

    this.app.innerHTML = `
      ${renderHeader()}
      ${renderHero()}
      ${renderStats()}
      ${renderCategories(this.activeCategory)}
      ${renderCourseGrid(filteredCourses)}
      ${renderFeatures()}
      ${renderFooter()}
    `;
  }

  private setupEventListeners(): void {
    this.app.addEventListener('click', (e: Event) => {
      const target = e.target as HTMLElement;
      
      if (target.matches('[data-category]')) {
        this.activeCategory = target.dataset.category || 'all';
        this.render();
        this.setupEventListeners();
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new YogaApp();
});
