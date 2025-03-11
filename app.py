import streamlit as st
from PIL import Image
from openai import OpenAI
import requests
from io import BytesIO

# 设置 Deepbricks 中介的 API 密钥和基础 URL
API_KEY = "sk-KACPocnavR6poutXUaj7HxsqUrxvcV808S2bv0U9974Ec83g"
BASE_URL = "https://api.deepbricks.ai/v1/"

# 初始化 OpenAI 客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 函数：根据提示词生成图像
def generate_image(prompt):
    resp = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024",
        quality="hd"
    )
    # 检查响应并获取生成图像的 URL
    if resp and hasattr(resp, "data") and resp.data and hasattr(resp.data[0], "url"):
        image_url = resp.data[0].url
        # 使用图片 URL 下载图片
        image_resp = requests.get(image_url)
        if image_resp.status_code == 200:
            return Image.open(BytesIO(image_resp.content))
    return None

# Streamlit 界面
st.title("个性化定制衣服生成系统")

# 加载基础白衬衫图片（请确保文件路径正确）
shirt_image = Image.open('white_shirt.png')
st.sidebar.image(shirt_image, caption="基础白衬衫", use_column_width=True)

# 用户输入定制提示词
prompt = st.text_input("请输入您想要的定制设计提示词", "例如：花卉图案，抽象艺术")

# 当用户点击按钮时，调用接口生成设计图
if st.button("生成定制衣服设计"):
    if prompt:
        custom_design = generate_image(prompt)
        if custom_design:
            # 调整生成的设计图大小以匹配白衬衫图像
            custom_design = custom_design.resize(shirt_image.size)
            try:
                # 尝试将生成的设计图叠加到白衬衫上（要求生成图像支持透明通道）
                shirt_image.paste(custom_design, (0, 0), custom_design)
            except ValueError:
                # 如果生成图没有透明通道，则直接粘贴
                shirt_image.paste(custom_design, (0, 0))
            st.image(shirt_image, caption="您的个性化定制衣服设计", use_column_width=True)
        else:
            st.error("生成图像失败，请稍后重试。")
    else:
        st.warning("请输入有效的提示词！")
