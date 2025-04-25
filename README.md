# easymcps
基于openmanus 增加web对话窗口、扩展了mcptools、增加多场景自由组合mcp

这是一个学习测试项目  对大模型mcp规划有兴趣的同学可以参考玩一下 过程遇到问题记录一下
测试使用阿里百炼的qwen-plus系列还比较智能  现在每个小版本免费100万token 基本能放心使用 及时超了费用也不贵
主要功能
1.web对话窗口
openmanus 本身只支持启动程序输入框输入对话、使用fastapi增加web对话窗口 ，支持从step中判定答案或者展示所有step输出、支持清除当前对话上下文
2.mcp支持
在原有tools基础上  支持python、js类型的mcp python直接下载源码到servers/python下 js需全局安装后将可npx执行的包拷贝到servers/js下 然后使用package.json中的bin文件测试过一些都是OK的
3.mcp多scene管理
mcp过多会消耗tokens 而且模型理解也有问题  需要结合场景动态组合，简单做了支持mcp工具场景化动态加载支持
4.测试打包
已经完成最基本exe打包 并跑通高德地图的规划请求

遗留问题：

1.UI很原始 全是AI自己生成  交互bug很多 只是示意
2.python_execute即使执行很简单简单语句也很慢 
3.对话只是简单的把部分信息从messages拿出来 特别是只显示结果判定逻辑有问题 考虑需要给模型在终止工具之前一个最终总结的提示优化
4.多场景只做了最粗糙的验证 可以作为参考
5.打包问题比较多 主要有包比较大、多进程时--name--竟然也是main导致重新绑定端口失败程序退出、playwright单独安装没弄、tiktoken_ext这个包打不进去要手动处理


