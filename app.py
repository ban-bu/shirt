import streamlit as st
from PIL import Image
import requests
from io import BytesIO
import cairosvg

# 关键：导入 st_canvas
from streamlit_drawable_canvas import st_canvas

# 如果你使用 Deepbricks 中介 OpenAI，请引入并配置：
from openai import OpenAI

API_KEY = "YOUR_API_KEY"  # 请妥善保管，不要在公开场合直接暴露
BASE_URL = "https://api.deepbricks.ai/v1/"

# 初始化 OpenAI 客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def generate_vector_image(prompt: str):
    """
    调用 Deepbricks 图像生成接口。如果响应为 SVG，则用 cairosvg 转为 PNG；
    否则直接用 PIL 打开。
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
                    # 如果是 SVG 则转换为 PNG
                    try:
                        png_data = cairosvg.svg2png(bytestring=image_resp.content)
                        return Image.open(BytesIO(png_data))
                    except Exception as conv_err:
                        st.error(f"SVG 转 PNG 时出错: {conv_err}")
                        return None
                else:
                    # 否则直接打开位图
                    return Image.open(BytesIO(image_resp.content))
            else:
                st.error(f"下载图像失败，状态码：{image_resp.status_code}")
        except Exception as download_err:
            st.error(f"请求图像时出错: {download_err}")
    else:
        st.error("未能从 API 响应中获取图像 URL。")
    return None

# ============ Streamlit 应用界面 ============

st.title("可拖动定制图案位置的衣服生成系统")

# 1. 加载衬衫底图
try:
    shirt_image = Image.open("white_shirt.png").convert("RGBA")
except Exception as e:
    st.error(f"加载白衬衫图片时出错: {e}")
    st.stop()

shirt_w, shirt_h = shirt_image.size

# 2. 用户输入定制提示
st.subheader("请输入您的个性化定制需求：")
prompt = st.text_input("设计提示词 (必填)", "A colorful floral pattern")

# 3. 使用 st_canvas 在衬衫图片上拖动矩形
st.write("在下方画布上拖动一个矩形来指定图案摆放区域：")

# 创建可绘制画布
canvas_result = st_canvas(
    fill_color="rgba(255, 0, 0, 0.2)",   # 绘制矩形的填充色（半透明红色）
    stroke_width=2,
    stroke_color="red",                 # 边框颜色
    background_image=shirt_image,       # 背景：白衬衫图
    update_streamlit=True,
    width=shirt_w,
    height=shirt_h,
    drawing_mode="rect",               # 只允许画矩形
    key="canvas"
)

st.caption("提示：如需调整矩形，可在工具栏中选择 'Select' 模式后拖动/缩放已画好的矩形。")

# 4. 点击按钮后，调用 AI 接口并合成图案
if st.button("生成定制衣服设计"):
    # 确保用户输入了提示词
    if prompt.strip():
        # 从 canvas_result 获取最后一个绘制的矩形数据
        if canvas_result.json_data is not None:
            objects = canvas_result.json_data.get("objects", [])
            if objects:
                # 假设我们取最后一个矩形
                rect = objects[-1]
                left = rect["left"]
                top = rect["top"]
                width = rect["width"]
                height = rect["height"]

                # 生成图案
                custom_design = generate_vector_image(prompt)
                if custom_design:
                    # 按矩形大小缩放图案
                    custom_design = custom_design.resize(
                        (int(width), int(height)), Image.LANCZOS
                    )

                    # 合成：把图案贴到衬衫图像相应位置
                    composite_image = shirt_image.copy()
                    try:
                        composite_image.paste(custom_design, (int(left), int(top)), custom_design)
                    except Exception as e:
                        st.warning(f"使用透明通道粘贴失败，直接粘贴: {e}")
                        composite_image.paste(custom_design, (int(left), int(top)))

                    st.image(composite_image, caption="您的个性化定制衣服设计", use_column_width=True)
                else:
                    st.error("生成图像失败，请稍后重试。")
            else:
                st.warning("请先在画布上绘制一个矩形来指定图案位置！")
    else:
        st.warning("请先输入设计提示词。")
