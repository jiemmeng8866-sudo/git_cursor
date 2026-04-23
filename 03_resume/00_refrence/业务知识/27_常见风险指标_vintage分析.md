# vintage分析

## 1 业务含义

***vintage分析（账龄分析）***用于分析不同观察时期下客户随着账龄增长（账户成熟期）下的风险增长变化规律;【其中，以放款月为基准月，账龄（mob）表示同一笔放款借据的放款月至观察月的月份（放款当月的账龄为0）】

![image-20260214130323739](C:\Users\m8705\AppData\Roaming\Typora\typora-user-images\image-20260214130323739.png)



vintage分析常用于观察不同月份下的客群随着账龄增加的的逾期/不良率的变化情况，其中可获取其客群质量的稳定性（vintage值是否趋于稳定、同账龄客群的违约分布是否出现倒三角现象等）、客群的平均生命周期（客户质量变坏的周期）、客群的异常情况（是否存在异常月份等），进行监控预警，及时分析策略调整的方向，确定风险暴露的表现期，有利于在不同时期立体展示多维度数据和同步比较，综合决策。

***vintage-常见的报告口径：***

（1）发放时点-客户/金额维度-vintage(不良/逾期)：一般用于资产质量测算（时点逾期情况） （2）首借时点/首授时点-客户维度-vintage(不良/逾期T+N)：一般用于不同客群资产质量比较和策略效果跟踪（历史逾期情况）

![image-20260214130332775](C:\Users\m8705\AppData\Roaming\Typora\typora-user-images\image-20260214130332775.png)



***vintage-集市中间表：***中间表的加工逻辑、数据字典及使用方法可参考复杂风险指标-中间表专区；其中首授时点可参考首授时点-代码文档；

| 报告口径                          | 表名                                 | 粒度            | 更新     | 计算口径                 |
| --------------------------------- | ------------------------------------ | --------------- | -------- | ------------------------ |
| 微业贷-发放时点-vintage           | dwd_ffsd_vintage_by_duebill_ds_nowyd | 借据号+观察时点 | 每日更新 | 不良/逾期(T+N)           |
| 微业贷-首借时点-vintage           | dwd_sjsd_vintage_by_duebill_ds       | 借据号+观察时点 | 月末更新 | 逾期(T+N)                |
| 微业贷-首授时点-vintage           | dwd_sxsd_vintage_by_duebill_ds       | 借据号+观察时点 | 月末更新 | 逾期(T+N)                |
| 微业贷-最新授信时点-vintage       | dwd_new_sxsd_vintage_by_duebill_ds   | 借据号+观察时点 | 月末更新 | 逾期(T+N)                |
| 微众易贷-发放时点（还原）-vintage | dwd_ffsd_vintage_by_duebill_ds_wzyd  | 借据号+观察时点 | 月末更新 | 不良/逾期(T+N)/td>       |
| 微众易贷-不还原时点-vintage       | dwd_rysd_vintage_by_duebill_ds_wzyd  | 借据号+观察时点 | 月末更新 | 首借/首授/发放-逾期(T+N) |

***参考资料：***

[（1）信贷风控中Vintage、滚动率、迁移率的理解](https://zhuanlan.zhihu.com/p/81027037) [（2）Vintage分析表计算过程详解](https://zhuanlan.zhihu.com/p/163206686)

## 2 计算全流程

### 2.1 发放时点-金额维度-vintage

***Step1 - 限定待观察的借据范畴：***

（1）剔除冲销的借据：duestatus in ('0','1','2','3')（2）剔除万一贷的借据：nvl(is_oneyidai_vintage,0) <> 1  （3）不含新借据，保留最原始的借据号（如借新还旧、无还本续贷），需进行借据还原重组发放时点-不良vintage指标需将新借据号还原成旧借据号，但仍以新借据的余额、逾期天数、五级分类为主，且为尽量还原资产真实情况，不良资产转让后，借据余额、逾期天数、五级分类均需按封包时点进行还原：转让后的借据的duestatus会变成结清，且余额为0，若不进行借据还原，直接计算会少算了部分余额。

***Step2 - 锚定基准月（发放月）计算账龄：观察时点与发放月份的月份差（账龄mob）：***

```Plaintext
,months_between(from_unxitime(unix_timestamp(ds,'yyyyMMdd'),yyyy-MM'),putout_month) as mob
```

***Step3 - 分子：计算各发放月份下的不同账龄下的时点不良金额/时点逾期金额：***

```Plaintext
,sum(case when classifyresult in ('03','04','05') then balance else 0 end) as bl_amt                    --不良金额
,sum(case when overduedays > 0 then balance else 0 end) as yq_amt                                                            --逾期金额
```

***Step4 - 分母：计算各发放月份内的在贷客户数/在贷金额：***

```Plaintext
,count(distinct case when duestatus in ('0','1','2','3') then ccif else null end) as ccif--在贷客户数
,sum(case when duestatus in ('0','1','2','3') then businesssum else 0 end) as businesssum--在贷金额
```

***Step5：计算发放时点-不良/逾期vintage***

| 计算指标         | 分子             | 分母             |
| ---------------- | ---------------- | ---------------- |
| 客户(金额)不良率 | 不良客户数(金额) | 在贷客户数(金额) |
| 客户(金额)逾期率 | 逾期客户数(金额) | 在贷客户数(金额) |

### 2.2 首借时点/首授时点-客户维度-vintage

***Step1 - 限定待观察的借据范畴：***剔除冲销的借据、包含万一贷的借据；

（1）取客户最早一笔借据的发放月份为首借月份first_putout_month；

（2）取客户最早一次授信成功的流水的月份为首授月份first_souxin_month（注：关联核额流水表取最早核额成功的授信时点）；

***Step2 - 锚定基准月（发放月）计算账龄：***观察时点与首借月份/首授月份的月份差（账龄mob）：

```Plaintext
,cast(months_between(from_unixtime(unix_timestamp(t2.ds,'yyyyMMdd'),'yyyy-MM'),first_putout_month) as bigint) as mob
,cast(months_between(from_unixtime(unix_timestamp(t2.ds,'yyyyMMdd'),'yyyy-MM'),first_souxin_month) as bigint) as mob
```

***Step3 - 分子：***计算首借月份/首授月份的不同账龄下的不良客户数/历史最大逾期T+N的客户数**（假设N = 60）**：

```Plaintext
,count(distinct case when classifyresult in ('03','04','05') then ccif end) as bl_cnt --不良客户数
,count(distinct case when max_overduedays > 60 then ccif end) as yq_cnt -- 逾期T+60客户数
```

➤ 一般首借/首授时点等的逾期逻辑取借据的历史最大逾期天数（一般从还款计划表中取观察时点下的最大逾期天数，建议先获取借据维度的最大逾期天数，更便于筛选出想分析的借据范畴，再进一步判断客户的逾期情况）。

```Plaintext
--最大逾期天数的参考代码：取月末分区即可，之后根据借据号（或客户号ccif）关联回去
select ds,duebill_serialno,max(overduedays_duebill) as max_overduedays
from brm_ent_dm_work.dwd_mcfcm_payment_schedule_ds
where substr(date_add(from_unixtime(unix_timestamp(ds,'yyyyMMdd'),'yyyy-MM-dd'),1),9,2) = '01' and duestatus_run_date in ('0','1','2','3')
group by ds,duebill_serialno
```

***Step4 - 分母：***计算首借月份/首授月份的在贷客户数：

```Plaintext
,count(distinct case when duestatus in ('0','1','2','3') then ccif end) as cnt
```

***Step5 - vintage计算：***客户逾期（不良）率 = 逾期（不良）客户数 / 在贷客户数

## 3 发放时点-vintage-不良资产转让还原

```SQL
--Step1: 发放时点的不良vintage需进行不良资产转让还原
select t.duebill_serialno,
       t.ds,
       t.putout_date,
       from_unixtime(unix_timestamp(t.ds,'yyyyMMdd'),'yyyy-MM-dd') as ds_std_origin,
       t.ds_month,
       t2.origin_duebill_serialno,
       case when t1.duebill_serialno is not null and t1.package_date <= t.ds and coalesce(t.is_xwyy_21,0) = 1 then t1.package_amt + coalesce(t.un_balance_xwyy_21,0)
            when t1.duebill_serialno is not null and t1.package_date <= t.ds then t1.package_amt
            when bw.duebill_serialno is not null and bw.trans_date <= t.ds then bw.balance
            else t.balance end as balance, --余额还原
       case when t1.duebill_serialno is not null and t1.package_date <= t.ds then '05'
            when bw.duebill_serialno is not null and bw.trans_date <= t.ds then bw.classifyresult 
            else t.classifyresult end as classifyresult, --五级分类还原
       case when t1.duebill_serialno is not null and t1.package_date <= t.ds then package_overduedays_before
            when bw.duebill_serialno is not null and bw.trans_date <= t.ds then bw.overduedays 
            else t.overduedays end as overduedays, --逾期天数还原
       case when t1.duebill_serialno is not null and t1.package_date <= t.ds then duestatus_before
            when bw.duebill_serialno is not null and bw.trans_date <= t.ds then bw.duestatus 
            else t.duestatus end as duestatus  --借据状态还原
from(--集市表
        select duebill_serialno,balance,classifyresult,overduedays,duestatus,ds,putout_date,un_balance_xwyy_21,is_xwyy_21,from_unixtime(unix_timestamp(ds,'yyyyMMdd'),'yyyy-MM') as ds_month
        from brm_ent_dm_work.dwd_mcfcm_business_duebill_etl_ds
        where ds >= '20170101' and length(ds) = 8 and ds <= '${run_date}'
        and substr(date_add(from_unixtime(unix_timestamp(ds,'yyyyMMdd'),'yyyy-MM-dd'),1),9,2) = '01' 
)t        
left join(--常用的表内不良资产转让
        select duebill_serialno,package_amt,replace(substr(package_date,1,10),'-','') as package_date,package_overduedays_before, duestatus_before
        from brm_ent_dm_work.dwd_duebill_blzczr_ds
        where ds = '${run_date}'
)t1 on t.duebill_serialno = t1.duebill_serialno    
left join(--表外的不良资产转让 20240129转让
        select duebill_serialno,balance,classifyresult,overduedays,duestatus,replace(substr(transdate,1,10),'-','') as trans_date
        from brm_ent_dm_work.dwd_duebill_bw_blzczr_20240131
)bw on t.duebill_serialno = bw.duebill_serialno 
left join(--新旧借据的映射表 还原至非万一贷的那笔
        select duebill_serialno,origin_duebill_serialno
        from brm_ent_dm_work.dwd_duebill_mapping_origin_not_is_wyd
        where ds = '${run_date}'
)t2 on t.duebill_serialno = t2.duebill_serialno
```