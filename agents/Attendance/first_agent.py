import os
from openai import OpenAI
from dotenv import load_dotenv

# 1. 加载环境变量
# 因为你的 .env 文件在上一级目录 (workspace)，所以我们要指定路径
# 如果 .env 和代码在同一个文件夹，直接 load_dotenv() 就行
env_path = os.path.join(os.path.dirname(__file__), '../../.env')
if load_dotenv(env_path):
    print("✅ 成功加载 .env 文件")
else:
    print("❌ 未找到 .env 文件，请检查路径")

# 2. 从 .env 文件里提取 API Key
# 这里的 "DEEPSEEK_API_KEY" 必须和你 .env 文件里写的名字一模一样！
api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    print("❌ 错误：未找到 API Key，请检查 .env 文件内容")
else:
    print(f"✅ API Key 读取成功: {api_key[:5]}******") # 只打印前几位，确保安全

# 3. 初始化连接器 (Client)
# base_url 是 DeepSeek 的官方地址，api_key 就是刚才读出来的密码
client = OpenAI(
    api_key=api_key, 
    base_url="https://api.deepseek.com" 
)

# 4. 发送请求 (这是最核心的一步！)
print("🚀 正在呼叫 DeepSeek，请稍候...")
try:
    response = client.chat.completions.create(
        model="deepseek-chat",  # 指定要调用的模型名字
        messages=[
            {"role": "system", "content": "你是一个乐于助人的AI编程助手。"},
            {"role": "user", "content": "你好！我是从产品经理转型的开发者，这是我写的第一行智能体代码，请用一句简短的话鼓励我。"}
        ],
        stream=False
    )

    # 5. 打印结果
    print("\n" + "="*30)
    print("🤖 AI 的回复：")
    print(response.choices[0].message.content)
    print("="*30 + "\n")

except Exception as e:
    print(f"\n❌ 调用失败: {e}")