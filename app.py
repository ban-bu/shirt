import streamlit as st
from PIL import Image
from openai import OpenAI
import requests
from io import BytesIO
import cairosvg

# 设置 Deepbricks 中介的 API 密钥和基础 URL
API_KEY = "sk-KACPocnavR6poutXUaj7HxsqUrxvcV808S2bv0U9974Ec83g"  # 请勿公开真实密钥
BASE_URL = "https://api.deepbricks.ai/v1/"

# 初始化 OpenAI 客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 函数：根据提示词生成矢量图（SVG），并转换为 PIL Image
def generate_vector_image(prompt):
    resp = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024",
        quality="hd",
        format="svg"  # 请求返回矢量图
    )
    # 检查响应并获取生成图的 URL
    if resp and hasattr(resp, "data") and resp.data and hasattr(resp.data[0], "url"):
        image_url = resp.data[0].url
        image_resp = requests.get(image_url)
        if image_resp.status_code == 200:
            # 将 SVG 转换为 PNG 数据
            png_data = cairosvg.svg2png(bytestring=image_resp.content)
            return Image.open(BytesIO(png_data))
    return None

# Streamlit 用户界面
st.title("个性化定制衣服生成系统")

# 加载基础白衬衫图片（请确保 'white_shirt.png' 路径正确）
shirt_image = Image.open('white_shirt.png')
st.sidebar.image(shirt_image, caption="基础白衬衫", use_column_width=True)

# 用户输入定制提示词
prompt = st.text_input("请输入您想要的定制设计提示词", "例如：花卉图案，抽象艺术")

if st.button("生成定制衣服设计"):
    if prompt:
        # 调用 API 生成矢量图设计
        custom_design = generate_vector_image(prompt)
        if custom_design:
            # 调整生成的设计图为合适尺寸（此处可根据需求调整比例）
            # 例如，将设计图宽度设为白衬衫宽度的50%
            shirt_w, shirt_h = shirt_image.size
            design_w = int(shirt_w * 0.5)
            # 保持宽高比调整高度
            design_ratio = custom_design.width / custom_design.height
            design_h = int(design_w / design_ratio)
            custom_design = custom_design.resize((design_w, design_h), Image.ANTIALIAS)
            
            # 计算将设计图粘贴在衬衫正中间的位置
            pos_x = (shirt_w - design_w) // 2
            pos_y = (shirt_h - design_h) // 2
            
            # 复制白衬衫图像，进行叠加操作
            composite_image = shirt_image.copy()
            try:
                # 如果设计图具有透明通道，则使用其作为 mask
                composite_image.paste(custom_design, (pos_x, pos_y), custom_design)
            except ValueError:
                # 否则直接粘贴
                composite_image.paste(custom_design, (pos_x, pos_y))
            
            # 显示最终合成的图像
            st.image(composite_image, caption="您的个性化定制衣服设计", use_column_width=True)
        else:
            st.error("生成图像失败，请稍后重试。")
    else:
        st.warning("请输入有效的提示词！")
