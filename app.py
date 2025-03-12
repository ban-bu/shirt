import streamlit as st
from PIL import Image, ImageDraw
from openai import OpenAI
import requests
from io import BytesIO
import cairosvg

# ========== 配置信息 ==========
API_KEY = "YOUR_API_KEY"  # 请妥善保管密钥
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

# 1. 加载基础白衬衫图片
try:
    base_image = Image.open('white_shirt.png').convert("RGBA")
except Exception as e:
    st.error(f"加载白衬衫图片时出错: {e}")
    st.stop()

# 2. 定义衬衫在整张图片中的可视区域 (shirt_x, shirt_y, shirt_w, shirt_h)
#    需要根据你的图片实际情况做微调，让它尽可能准确地覆盖实际衣服部分
shirt_x = 100  # 衬衫区域左上角 x 坐标
shirt_y = 50   # 衬衫区域左上角 y 坐标
shirt_w = 300  # 衬衫区域的宽度
shirt_h = 500  # 衬衫区域的高度

# 3. 输入个性化参数
st.subheader("请输入您的个性化定制需求：")
theme = st.text_input("主题或关键词 (必填)", "花卉图案")
style = st.text_input("设计风格 (如 abstract, cartoon, realistic 等)", "abstract")
colors = st.text_input("偏好颜色 (如 pink, gold, black)", "pink, gold")
details = st.text_area("更多细节 (如 swirling shapes, futuristic touches)", "some swirling shapes")

# 4. 选择图案在“衬衫区域”内的对齐方式
st.subheader("选择图案在衬衫上的位置：")
horizontal_pos = st.radio("水平方向", options=["左侧", "居中", "右侧"], index=1)
vertical_pos = st.radio("垂直方向", options=["上方", "居中", "下方"], index=1)

# 5. 预览衬衫区域 + 对齐位置（示意红框）
preview_image = base_image.copy()
draw = ImageDraw.Draw(preview_image)
# 先画出衬衫区域的边框（蓝色）
draw.rectangle(
    (shirt_x, shirt_y, shirt_x + shirt_w, shirt_y + shirt_h),
    outline="blue", width=3
)
# 在区域内放一个示例红框，用于大概显示图案大小
# 这里简单固定一个比例 (0.3 * 衬衫区域宽度)，并假设 1:1 比例
preview_design_w = int(shirt_w * 0.3)
preview_design_h = preview_design_w

# 计算示例红框在衬衫区域内的位置
if horizontal_pos == "左侧":
    preview_pos_x = shirt_x
elif horizontal_pos == "居中":
    preview_pos_x = shirt_x + (shirt_w - preview_design_w) // 2
else:  # "右侧"
    preview_pos_x = shirt_x + (shirt_w - preview_design_w)

if vertical_pos == "上方":
    preview_pos_y = shirt_y
elif vertical_pos == "居中":
    preview_pos_y = shirt_y + (shirt_h - preview_design_h) // 2
else:  # "下方"
    preview_pos_y = shirt_y + (shirt_h - preview_design_h)

draw.rectangle(
    (preview_pos_x, preview_pos_y, preview_pos_x + preview_design_w, preview_pos_y + preview_design_h),
    outline="red", width=3
)

st.image(preview_image, caption="蓝框：衬衫可视区域  |  红框：图案示例位置", use_column_width=True)

# 6. 生成定制衣服设计
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
            # 将生成的设计图缩放到衬衫区域的 0.3（或你想要的其他比例）
            scale_ratio = 0.3
            design_w = int(shirt_w * scale_ratio)
            # 按照实际宽高比缩放
            design_ratio = custom_design.width / custom_design.height
            design_h = int(design_w / design_ratio)
            custom_design = custom_design.resize((design_w, design_h), Image.LANCZOS)

            # 根据用户选择，计算粘贴位置
            if horizontal_pos == "左侧":
                pos_x = shirt_x
            elif horizontal_pos == "居中":
                pos_x = shirt_x + (shirt_w - design_w) // 2
            else:  # "右侧"
                pos_x = shirt_x + (shirt_w - design_w)

            if vertical_pos == "上方":
                pos_y = shirt_y
            elif vertical_pos == "居中":
                pos_y = shirt_y + (shirt_h - design_h) // 2
            else:  # "下方"
                pos_y = shirt_y + (shirt_h - design_h)

            composite_image = base_image.copy()
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
