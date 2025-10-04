# 用户画像与词汇存储设计文档

## 1. 背景
为了在 **mem0 框架**中实现用户画像与词汇管理功能，我们需要对数据进行结构化存储与动态扩展：
- **基础信息** → 结构化字段，稳定不变，适合 MySQL。
- **额外画像** → 动态扩展，数组/嵌套对象较多，适合 MongoDB。
- **词汇掌握** → 高度结构化，涉及统计与聚合分析，适合 MySQL。
- 在接口层提供 set_profile / get_profile 和 set_vocab / get_vocab 四个方法，屏蔽底层 MySQL/Mongo 的差异，统一对外暴露。

目标：
- 提供用户画像的完整建模。
- 支持兴趣、技能等动态扩展字段。
- 支持对词汇的增删查改及统计。

---

## 2. 存储方案概览
- **MySQL**
  - `user_profile`: 用户基础特征（稳定字段）。
  - `user_vocabulary`: 用户掌握的词汇（结构化、支持聚合统计）。
- **MongoDB**
  - `user_additional_profile`: 用户扩展特征（兴趣、技能、性格、社交）。

---

## 3. 数据库 Schema 设计

### 3.1 用户基本特征表 (`user_profile`) – MySQL
存储用户基础信息，字段稳定，不常变动。

```sql
CREATE TABLE user_profile (
    user_id VARCHAR(50) PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    name VARCHAR(100),
    nickname VARCHAR(100),
    english_name VARCHAR(100),
    age INT,
    birthday DATE,
    gender ENUM('M','F'),
    nationality VARCHAR(50),
    hometown VARCHAR(100),
    timezone VARCHAR(50)
);
```

数据示例：
```json
{
  "user_id": "u123",
  "created_at": "2025-10-01",
  "updated_at": "2025-10-03",
  "name": "爱丽丝",
  "nickname": "小艾",
  "english_name": "Alice",
  "age": 7,
  "birthday": "2018-07-15",
  "gender": "F",
  "nationality": "China",
  "hometown": "Nanjing",
  "timezone": "Asia/Shanghai"
}
```

### 3.2 用户扩展特征集合 (user_additional_profile) – MongoDB

存储动态扩展的用户画像，字段不固定。
```json
{
  "user_id": "u123",
  "interests": ["football", "lego", "anime"],
  "skills": ["math", "python"],
  "personality": ["extroverted", "curious"],
  "social_context": {
    "father": {
      "name": "John",
      "career": "doctor",
      "info": ["kind and loving", "plays football"]
    },
    "mother": {
      "name": "Mary",
      "career": "teacher",
      "info": ["strict", "cooks delicious meals"]
    },
    "family_members": ["grandmother", "uncle"],
    "friends_peers": ["Tom", "Jerry"]
  },
  "system_metadata": {
    "created_at": "2025-10-01",
    "updated_at": "2025-10-03"
  }
}
```


索引建议：
```python
db.user_additional_profile.createIndex({ "user_id": 1 }, { unique: true })
db.user_additional_profile.createIndex({ "interests": 1 })
db.user_additional_profile.createIndex({ "skills": 1 })
```

### 3.3 用户词汇表 (user_vocabulary) – MySQL

存储用户掌握的词汇，支持聚合统计。
```sql
CREATE TABLE user_vocabulary (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    word VARCHAR(100) NOT NULL,
    level ENUM('learned','practicing','mastered') NOT NULL,
    count INT DEFAULT 0,
    last_seen DATETIME,
    UNIQUE(user_id, word),
    INDEX(user_id),
    INDEX(word)
);
```


数据示例：
```json
{ 
  "user_id": "u123",
  "word": "apple",
  "level": "mastered",
  "count": 5,
  "last_seen": "2025-10-03"
}
```

---

## 4. 特征提取、更新与输出

### 4.1 信息提取

这里我们参考 mem0 的设计，对外提供两个接口：**set_profile**、**set_vocab**。  
分别对应更新用户信息（包括基本信息和拓展信息）和更新用户词汇。

#### **set_profile 更新用户信息接口**
- 并行调用两个 LLM：
  - 一个分析基本信息（basic info，MySQL 存储）是否需要新增或更新信息（这里不考虑删除）。  
  - 一个分析扩展信息（additional profile，MongoDB 存储）是否需要新增、更新或删除（参考 mem0 的 merge 方法和 prompt）。  

#### **set_vocab 更新用户词汇接口**
- 调用一个 LLM（一次），提取本次对话或会话涉及的词汇及其掌握程度：  
```json
  [
    { "word": "apple", "level": "mastered" },
    { "word": "banana", "level": "practicing" }
  ]
```

-   在程序内进行合并逻辑（无需再次调用 LLM）：
    -   若词汇不存在 → 新增记录。
    -   若词汇存在 → 更新 `count`、`last_seen`，必要时更新 `level`。

### 4.2 信息输出

对外提供两个接口：**get\_profile**、**get\_vocab**。

#### **get\_profile 读取用户信息接口**

-   入参：`uid, type, field`
-   行为：
    -   `type=0` → 返回用户基本信息（MySQL 中的字段）。
    -   `type=1 且 field=""` → 返回用户所有扩展画像（Mongo）。
    -   `type=1 且 field="xxx"` → 返回 Mongo 中对应字段。
    -   **支持点语法（dot notation）**，如 `field="social_context.father.name"` → 返回具体值。
        

#### **get\_vocab 读取用户词汇接口**

-   入参：`uid, word, filter`
-   行为：
    -   `word="" 且 filter={}` → 返回用户所有词汇。
    -   `word="apple"` → 返回该用户的单个词汇记录。
    -   `filter` → 支持条件筛选，例如：
        
        ```json
        { "level": "mastered" }
        { "last_seen": { "$gt": "2025-10-01" } }
        ```
        
        可实现“查询所有已掌握的词汇”、“查询最近 7 天更新的词汇”等。

### 4.3 接口设计总结

-   **set\_profile**：负责更新基础信息（MySQL）和扩展信息（Mongo），参考 mem0 的 merge 逻辑。
-   **set\_vocab**：负责更新词汇，LLM 只做识别，新增/更新由程序逻辑完成。
-   **get\_profile**：支持精细化读取（点语法），便于查询特定字段。
-   **get\_vocab**：支持单词查询和条件过滤，扩展性强。

---

## 5. 注意事项

### 5.1 MySQL + Mongo 混合存储
- 稳定字段 → MySQL（强一致性、易统计）。
- 动态字段 → Mongo（灵活扩展、数组友好）。

### 5.2 数据一致性
- 通过 user_id 作为跨库唯一标识。

### 5.3 扩展性
- 后续新增特征时只需在 Mongo 增字段，不影响 MySQL。

### 5.4 统计需求
   - 画像类统计（兴趣、技能） → Mongo 聚合。
   - 词汇统计（全局 topN、个人进度） → MySQL 聚合。

### 5.5 支持点语法（dot notation）
- 查询扩展画像的嵌套字段，例如：
- field="social_context.father.name" → 返回 "John"。

### 5.6 词汇接口支持 条件过滤（filter），如按 level、last_seen 查询，提升灵活性。

⸻

## 6. 总结

- 用户画像 = 两部分：
  - 基础信息（user_profile，MySQL）
  - 动态特征（user_additional_profile，Mongo）
- 词汇单独管理（user_vocabulary，MySQL）。
- 提取 → 更新 → 存储 形成闭环。
- 混合存储兼顾 结构化查询 与 灵活扩展，符合实际业务需求。
- 接口层对外保持统一语义（set/get），内部自动路由到 MySQL 或 Mongo，便于维护与扩展
