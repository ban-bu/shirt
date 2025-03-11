import streamlit as st
from PIL import Image
from openai import OpenAI

# 设置 Deepbricks 中介的 API 密钥和基础 URL
API_KEY = "sk-y8x6LH0zdtyQncT0aYdUW7eJZ7v7cuKTp90L7TiK3rPu3fAg"
BASE_URL = "https://api.deepbricks.ai/v1/"

# 初始化 OpenAI 客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 函数：根据提示词生成图像
def generate_image_with_openai(prompt):
    completion = client.chat.completions.create(
        model="dall-e-3",
        messages=[
            {
                "role": "user",
                "content": f"Generate an image of a shirt with the following design: {prompt}"
            }
        ],
        stream=True
    )
    
    # 读取并返回生成的图像内容
    for chunk in completion:
        if 'choices' in chunk and 'delta' in chunk['choices'][0]:
            return chunk['choices'][0]['delta']
    return None

# Streamlit 界面
st.title("个性化定制衣服生成系统")

# 上传白衬衫图片
shirt_image = Image.open('white_shirt.png')
st.sidebar.image(shirt_image, caption="基础白衬衫", use_column_width=True)

# 输入框：让消费者输入提示词
prompt = st.text_input("请输入您想要的定制设计提示词", "例如：花卉图案，抽象艺术")

# 按钮：生成并显示图像
if st.button("生成定制衣服设计"):
    if prompt:
        # 使用 OpenAI 生成图像
        custom_design = generate_image_with_openai(prompt)

        if custom_design:
            # 将生成的图像叠加到白衬衫图像上
            custom_design = custom_design.resize(shirt_image.size)  # 调整大小匹配白衬衫图像
            shirt_image.paste(custom_design, (0, 0), custom_design)  # 将设计图像合成到衬衫上

            # 显示最终图像
            st.image(shirt_image, caption="您的个性化定制衣服设计", use_column_width=True)
    else:
        st.warning("请输入有效的提示词！")
