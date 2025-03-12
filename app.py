import streamlit as st
from PIL import Image, ImageDraw
from openai import OpenAI
import requests
from io import BytesIO
import cairosvg

# ========== 配置信息 ==========
API_KEY = "YOUR_API_KEY"  # 请妥善保管密钥
BASE_URL = "https://api.deepbricks.ai/v1/"
# =============================

# 初始化 OpenAI 客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def generate_vector_image(prompt):
    """
    根据提示词调用 Deepbricks 接口生成图像，
    如果响应为 SVG，则使用 cairosvg 转 PNG，
    否则直接返回位图 Image 对象。
    """
    try:
        resp = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard"
        )
    except Exception as e:
        st.error(f"调用 API 时出错: {e}")
        return None

    if resp and hasattr(resp, "data") and resp.data and hasattr(resp.data[0], "url"):
        image_url = resp.data[0].url
        try:
            image_resp = requests.get(image_url)
            if image_resp.status_code == 200:
                content_type = image_resp.headers.get("Content-Type", "")
                if "svg" in content_type.lower():
                    try:
                        png_data = cairosvg.svg2png(bytestring=image_resp.content)
                        return Image.open(BytesIO(png_data))
                    except Exception as conv_err:
                        st.error(f"SVG 转 PNG 时出错: {conv_err}")
                        return None
                else:
                    return Image.open(BytesIO(image_resp.content))
            else:
                st.error(f"下载图像失败，状态码：{image_resp.status_code}")
        except Exception as download_err:
            st.error(f"请求图像时出错: {download_err}")
    else:
        st.error("未能从 API 响应中获取图像 URL。")
    return None

# ========== Streamlit 应用界面 ==========

st.title("个性化定制衣服生成系统")

# 加载基础白衬衫图片（请确保 white_shirt.png 文件存在且路径正确）
try:
    shirt_image = Image.open('white_shirt.png')
except Exception as e:
    st.error(f"加载白衬衫图片时出错: {e}")
    st.stop()

st.sidebar.image(shirt_image, caption="基础白衬衫", use_column_width=True)

# 用户输入更多定制化参数
st.subheader("请输入您的个性化定制需求：")
theme = st.text_input("主题或关键词 (必填)", "花卉图案")
style = st.text_input("设计风格 (如 abstract, cartoon, realistic 等)", "abstract")
colors = st.text_input("偏好颜色 (如 pink, gold, black)", "pink, gold")
details = st.text_area("更多细节 (如 swirling shapes, futuristic touches)", "some swirling shapes")

# 自定义图案在衬衫上的显示参数
st.subheader("自定义图案在衬衫上的显示：")
scale_ratio = st.slider("图案尺寸比例（相对于衬衫宽度）", min_value=0.1, max_value=1.0, value=0.3, step=0.05)
offset_x = st.slider("X 方向偏移（正值向右，负值向左）", -200, 200, 0, step=5)
offset_y = st.slider("Y 方向偏移（正值向下，负值向上）", -200, 200, 0, step=5)

# 增加预览功能：点击按钮后显示一个带红框的预览图，标明图案将被放置的位置
if st.button("预览设计位置"):
    # 假设设计图宽高比未知时，默认按 1:1 比例预览
    default_ratio = 1.0
    shirt_w, shirt_h = shirt_image.size
    design_w = int(shirt_w * scale_ratio)
    design_h = int(design_w / default_ratio)
    # 计算预估粘贴位置：居中后加上偏移
    pos_x = (shirt_w - design_w) // 2 + offset_x
    pos_y = (shirt_h - design_h) // 2 + offset_y
    # 在衬衫图像上绘制红色边框预览区域
    preview_image = shirt_image.copy().convert("RGBA")
    draw = ImageDraw.Draw(preview_image)
    rect_coords = (pos_x, pos_y, pos_x + design_w, pos_y + design_h)
    draw.rectangle(rect_coords, outline="red", width=3)
    st.image(preview_image, caption="设计图预览位置", use_column_width=True)

# 点击生成按钮，调用 API 生成设计图，并将其叠加到 T 恤图片上
if st.button("生成定制衣服设计"):
    if theme.strip():
        # 拼接完整提示词
        prompt_text = (
            f"Create a unique T-shirt design. "
            f"Theme: {theme}. "
            f"Style: {style}. "
            f"Colors: {colors}. "
            f"Details: {details}. "
            f"Make it visually appealing."
        )
        custom_design = generate_vector_image(prompt_text)
        if custom_design:
            shirt_w, shirt_h = shirt_image.size
            # 使用生成图像实际宽高比来调整尺寸
            design_w = int(shirt_w * scale_ratio)
            design_ratio = custom_design.width / custom_design.height
            design_h = int(design_w / design_ratio)
            custom_design = custom_design.resize((design_w, design_h), Image.LANCZOS)
            
            pos_x = (shirt_w - design_w) // 2 + offset_x
            pos_y = (shirt_h - design_h) // 2 + offset_y
            
            composite_image = shirt_image.copy()
            try:
                composite_image.paste(custom_design, (pos_x, pos_y), custom_design)
            except Exception as e:
                st.warning(f"使用透明通道粘贴失败，直接粘贴: {e}")
                composite_image.paste(custom_design, (pos_x, pos_y))
                
            st.image(composite_image, caption="您的个性化定制衣服设计", use_column_width=True)
        else:
            st.error("生成图像失败，请稍后重试。")
    else:
        st.warning("请至少输入主题或关键词！")
