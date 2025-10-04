需要增加或调整几个接口：

1. 查询用户信息（根据uid直接进入数据库（pg和mongo）查询，返回全量信息）。这里tudo一下，鉴权（暂时不实现，但要todo记下来）
ji2. 返回空缺的字段（比如没有hometown，gender，但有name，那就返回[“hometown”,"gender"]），这个接口可以配置参数，返回pg中的空缺字段，返回mongo中的空缺，返回both的空缺。（我之所以要返回空缺，是可以告诉主服务缺这些信息，然后可以加入到给llm到prompt中，之后对话中可以尝试主动询问这些信息）
3. getprofile接口返回的内容，不是都有evidence吗？根据时间顺序（最新的优先）默认返回5条（可以配置，-1就是全部返回，但默认是5条）

有几个问题：

1. 我在docker还是看不到日志，你可以自己试试
2. mongo中的social_context字段，增加：
"teachers": [{
                "name": "Amy",
                "subject": "math",
                "info": ["kind and loving", "plays football"]
            },{...}]
"others": [{
                "name": "Jack",
                "subject": "friend", # relatives, friends, family, etc.
                "info": ["kind and loving", "plays football"]
            },{...}]