import streamlit as st
from PIL import Image
from openai import OpenAI
import requests
from io import BytesIO
import cairosvg

# 设置 Deepbricks 中介的 API 密钥和基础 URL
API_KEY = "sk-KACPocnavR6poutXUaj7HxsqUrxvcV808S2bv0U9974Ec83g"  # 请妥善保管，不要公开
BASE_URL = "https://api.deepbricks.ai/v1/"

# 初始化 OpenAI 客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def generate_vector_image(prompt):
    """
    根据提示词调用 Deepbricks 接口生成 SVG 矢量图，然后转换为 PNG 并返回 PIL Image 对象。
    """
    try:
        # 调用 Deepbricks 图像生成接口，请求返回 SVG 格式图像
        resp = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="hd",
            format="svg"
        )
    except Exception as e:
        st.error(f"调用 API 时出错: {e}")
        return None

    # 检查响应，获取图像 URL
    if resp and hasattr(resp, "data") and resp.data and hasattr(resp.data[0], "url"):
        image_url = resp.data[0].url
        try:
            image_resp = requests.get(image_url)
            if image_resp.status_code == 200:
                try:
                    # 将 SVG 数据转换为 PNG 数据
                    png_data = cairosvg.svg2png(bytestring=image_resp.content)
                    return Image.open(BytesIO(png_data))
                except Exception as conv_err:
                    st.error(f"SVG 转 PNG 时出错: {conv_err}")
                    return None
            else:
                st.error(f"下载图像失败，状态码：{image_resp.status_code}")
        except Exception as download_err:
            st.error(f"请求图像时出错: {download_err}")
    else:
        st.error("未能从 API 响应中获取图像 URL。")
    return None

# Streamlit 应用界面
st.title("个性化定制衣服生成系统")

# 加载基础白衬衫图片（确保 white_shirt.png 文件路径正确）
try:
    shirt_image = Image.open('white_shirt.png')
except Exception as e:
    st.error(f"加载白衬衫图片时出错: {e}")
    st.stop()

st.sidebar.image(shirt_image, caption="基础白衬衫", use_column_width=True)

# 用户输入提示词
prompt = st.text_input("请输入您想要的定制设计提示词", "例如：花卉图案，抽象艺术")

if st.button("生成定制衣服设计"):
    if prompt:
        custom_design = generate_vector_image(prompt)
        if custom_design:
            # 获取白衬衫图片尺寸
            shirt_w, shirt_h = shirt_image.size
            # 将生成的设计图调整为白衬衫宽度的 50%
            design_w = int(shirt_w * 0.5)
            design_ratio = custom_design.width / custom_design.height
            design_h = int(design_w / design_ratio)
            custom_design = custom_design.resize((design_w, design_h), Image.ANTIALIAS)
            
            # 计算将设计图置于白衬衫正中间的位置
            pos_x = (shirt_w - design_w) // 2
            pos_y = (shirt_h - design_h) // 2
            
            # 创建一个副本进行图像合成
            composite_image = shirt_image.copy()
            try:
                # 尝试使用设计图的透明通道作为蒙版进行粘贴
                composite_image.paste(custom_design, (pos_x, pos_y), custom_design)
            except Exception as e:
                # 如果失败，则直接粘贴
                st.warning(f"使用透明通道粘贴失败，直接粘贴: {e}")
                composite_image.paste(custom_design, (pos_x, pos_y))
                
            st.image(composite_image, caption="您的个性化定制衣服设计", use_column_width=True)
        else:
            st.error("生成图像失败，请稍后重试。")
    else:
        st.warning("请输入有效的提示词！")
