import streamlit as st
from PIL import Image
import requests
from io import BytesIO
import cairosvg

# 需要先安装: pip install streamlit-drawable-canvas
from streamlit_drawable_canvas import st_canvas

# ========== Deepbricks 配置信息，请自行替换 ==========
from openai import OpenAI
API_KEY = "YOUR_API_KEY"  # 不要在公开场合暴露真实密钥
BASE_URL = "https://api.deepbricks.ai/v1/"
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
# ==============================================

def generate_vector_image(prompt):
    """
    根据提示词调用 Deepbricks 接口生成图像。
    如果响应为 SVG，则用 cairosvg 转换为 PNG，否则直接返回位图。
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
                    # 若是 SVG，则先转换为 PNG
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


# ========== Streamlit 应用 ==========

st.title("可自由拖拽的个性化定制衣服生成系统")

# 1. 加载衬衫底图
try:
    base_image = Image.open("white_shirt.png").convert("RGBA")
except Exception as e:
    st.error(f"加载白衬衫图片时出错: {e}")
    st.stop()

# 2. 用户输入个性化参数
st.subheader("请输入您的个性化定制需求：")
theme = st.text_input("主题或关键词 (必填)", "花卉图案")
style = st.text_input("设计风格 (如 abstract, cartoon, realistic 等)", "abstract")
colors = st.text_input("偏好颜色 (如 pink, gold, black)", "pink, gold")
details = st.text_area("更多细节 (如 swirling shapes, futuristic touches)", "some swirling shapes")

st.write("---")
st.markdown("### 在下方画布上拖拽红框来决定图案放置的位置和大小：")
st.info("1. **选择 'Rect' 工具**\n"
        "2. 在衣服上 **拖拽** 出一个红框\n"
        "3. 可以 **移动/缩放** 红框\n"
        "4. 点右上角的 **X** 或按 ESC 键退出绘制模式")

# 3. 在画布上拖拽矩形
canvas_result = st_canvas(
    fill_color="rgba(255, 0, 0, 0.3)",  # 矩形内部半透明红色
    stroke_width=2,
    stroke_color="red",
    background_image=base_image,        # 衬衫作为背景
    update_streamlit=True,
    height=base_image.height,          # 画布高
    width=base_image.width,            # 画布宽
    drawing_mode="rect",               # 允许绘制矩形
    key="shirt_canvas"
)

# 4. 解析用户画的矩形数据（可能有多个，这里只取第一个）
rect_data = None
if canvas_result.json_data is not None:
    objects = canvas_result.json_data.get("objects", [])
    if len(objects) > 0:
        # 假设只使用用户绘制的最后一个矩形
        rect_data = objects[-1]

# 5. 点击“生成定制衣服设计”按钮，调用 API 并将图案放到红框处
if st.button("生成定制衣服设计"):
    if not theme.strip():
        st.warning("请至少输入主题或关键词！")
    else:
        if rect_data is None:
            st.warning("请先在画布上拖拽一个红框，用来放置图案！")
        else:
            # 生成图案
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
                # 解析矩形坐标和大小
                # left, top 为红框左上角坐标
                # width, height 为红框大小
                left = rect_data["left"]
                top = rect_data["top"]
                rect_w = rect_data["width"]
                rect_h = rect_data["height"]

                # 将生成图案缩放到红框大小
                custom_design = custom_design.resize((int(rect_w), int(rect_h)), Image.LANCZOS)

                # 在原图上合成
                composite_image = base_image.copy()
                try:
                    composite_image.paste(custom_design, (int(left), int(top)), custom_design)
                except Exception as e:
                    st.warning(f"使用透明通道粘贴失败，直接粘贴: {e}")
                    composite_image.paste(custom_design, (int(left), int(top)))

                st.image(composite_image, caption="您的个性化定制衣服设计", use_column_width=True)
            else:
                st.error("生成图像失败，请稍后重试。")
