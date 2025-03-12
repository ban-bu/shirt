import streamlit as st
from PIL import Image, ImageDraw
from openai import OpenAI
import requests
from io import BytesIO
import cairosvg

# ========== 配置信息 ==========
API_KEY = "sk-lNVAREVHjj386FDCd9McOL7k66DZCUkTp6IbV0u9970qqdlg"  # 请妥善保管密钥
BASE_URL = "https://api.deepbricks.ai/v1/"
# =================================

# 初始化 OpenAI 客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def generate_vector_image(prompt):
    """
    根据提示词调用 Deepbricks 接口生成图像，
    如果响应为 SVG，则使用 cairosvg 转为 PNG，
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

st.title("个性化定制衣服生成系统")

# 加载基础白衬衫图片（仅用于图像合成，不在侧边栏显示）
try:
    shirt_image = Image.open('white_shirt.png')
except Exception as e:
    st.error(f"加载白衬衫图片时出错: {e}")
    st.stop()

# 用户输入个性化参数
st.subheader("请输入您的个性化定制需求：")
theme = st.text_input("主题或关键词 (必填)", "花卉图案")
style = st.text_input("设计风格 (如 abstract, cartoon, realistic 等)", "abstract")
colors = st.text_input("偏好颜色 (如 pink, gold, black)", "pink, gold")
details = st.text_area("更多细节 (如 swirling shapes, futuristic touches)", "some swirling shapes")

st.subheader("选择图案在衬衫上的位置：")
# 使用单选按钮简化位置调节
horizontal_pos = st.radio("水平方向", options=["左侧", "中间", "右侧"], index=1)
vertical_pos = st.radio("垂直方向", options=["上侧", "中间", "下侧"], index=1)

# 自动生成预览位置（采用默认尺寸比例 0.3，用于预览）
shirt_w, shirt_h = shirt_image.size
preview_design_w = int(shirt_w * 0.3)
preview_design_h = preview_design_w  # 预览时采用1:1比例，仅供参考

if horizontal_pos == "左侧":
    preview_pos_x = 0
elif horizontal_pos == "中间":
    preview_pos_x = (shirt_w - preview_design_w) // 2
else:  # "右侧"
    preview_pos_x = shirt_w - preview_design_w

if vertical_pos == "上侧":
    preview_pos_y = 0
elif vertical_pos == "中间":
    preview_pos_y = (shirt_h - preview_design_h) // 2
else:  # "下侧"
    preview_pos_y = shirt_h - preview_design_h

preview_image = shirt_image.copy().convert("RGBA")
draw = ImageDraw.Draw(preview_image)
draw.rectangle(
    (preview_pos_x, preview_pos_y, preview_pos_x + preview_design_w, preview_pos_y + preview_design_h),
    outline="red",
    width=3
)
st.image(preview_image, caption="预览设计放置位置", use_column_width=True)

if st.button("生成定制衣服设计"):
    if theme.strip():
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
            # 生成图像实际尺寸采用 0.3 的比例
            design_w = int(shirt_w * 0.3)
            design_ratio = custom_design.width / custom_design.height
            design_h = int(design_w / design_ratio)
            custom_design = custom_design.resize((design_w, design_h), Image.LANCZOS)
            
            if horizontal_pos == "左侧":
                pos_x = 0
            elif horizontal_pos == "中间":
                pos_x = (shirt_w - design_w) // 2
            else:  # "右侧"
                pos_x = shirt_w - design_w

            if vertical_pos == "上侧":
                pos_y = 0
            elif vertical_pos == "中间":
                pos_y = (shirt_h - design_h) // 2
            else:  # "下侧"
                pos_y = shirt_h - design_h

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
