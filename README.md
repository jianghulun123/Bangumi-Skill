# Bangumi Skill

查 [Bangumi](https://bgm.tv) 番剧信息：搜索、详情、评分、短评。

## 安装

```bash
pip install -e .
# 或
pip install -r requirements.txt
```

**依赖**：`requests>=2.25.0` `beautifulsoup4>=4.9.0` · Python ≥ 3.8

## 使用

### 命令行

```bash
python -m bangumi.scripts.bangumi_crawler "葬送的芙莉莲"
```

### Python

```python
from bangumi import query_anime, format_detail

result = query_anime("孤独摇滚")
print(format_detail(result["detail"]))
```

输出示例：

```
# 孤独摇滚！
孤独摇滚！: Bangumi 评分 8.2 / 10，12000 人评分，排名 #23
放送日期：2022-10-09
标签：日常、音乐、搞笑、漫画改、百合、青春
简介：作为网络吉他手「吉他英雄」……

短评 / 风评摘录：
- 匿名（5星）：神作，年度最佳
- 用户A（4星）：演出力惊人
链接：https://bgm.tv/subject/384643
```

## API

所有函数签名和返回值详见源码注释。核心入口两个：

| 函数 | 说明 |
|------|------|
| `query_anime(keyword, comments_limit=8)` | 一步搜索→最佳匹配→详情+评分+短评 |
| `get_subject_detail(subject_id, comments_limit=8)` | 已知 ID 直接获取详情+评分+短评 |

底层函数（按需单独调用）：

| 函数 | 说明 |
|------|------|
| `search(keyword, limit=5)` → `list[dict]` | 搜索条目 |
| `get_subject(subject_id)` → `dict` | API 原始详情 |
| `get_rating(subject_id)` → `dict` | 评分摘要 |
| `get_comments(subject_id, limit=8)` → `list[dict]` | 网页短评 |

格式化函数：

| 函数 | 说明 |
|------|------|
| `format_detail(detail)` → `str` | 详情+评分+短评 |
| `format_search_results(results)` → `str` | 搜索结果 |
| `format_rating(rating)` → `str` | 单行评分 |

## 数据源

- **API 优先**：Bangumi v0 API (`api.bgm.tv/v0`)
- **HTML 降级**：搜索和短评在 API 不可用时自动解析网页
- 每次请求间隔 0.6s，15–20s 超时，统一 UA

## 许可

MIT
