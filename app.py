import streamlit as st
from PIL import Image
import requests
from io import BytesIO
import cairosvg
import os

# 导入 streamlit-drawable-canvas
from streamlit_drawable_canvas import st_canvas

# ========== Deepbricks/OpenAI 配置信息 ==========
from openai import OpenAI

API_KEY = "YOUR_API_KEY"  # 请替换为你自己的 API Key
BASE_URL = "https://api.deepbricks.ai/v1/"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def generate_vector_image(prompt: str):
    """
    调用 Deepbricks/OpenAI 接口，根据 prompt 生成图像。
    若返回 SVG，则用 cairosvg 转为 PNG；否则直接返回位图 Image。
    """
    try:
        resp = client.images.generate(
            model="dall-e-3",      # 确保该模型可用
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard"     # 标准画质
        )
    except Exception as e:
        st.error(f"调用 API 时出错: {e}")
        return None

    # 更新访问响应数据的方式，适配最新的OpenAI API
    if resp and len(resp.data) > 0 and resp.data[0].url:
        image_url = resp.data[0].url
        try:
            image_resp = requests.get(image_url)
            if image_resp.status_code == 200:
                content_type = image_resp.headers.get("Content-Type", "")
                if "svg" in content_type.lower():
                    try:
                        png_data = cairosvg.svg2png(bytestring=image_resp.content)
                        return Image.open(BytesIO(png_data)).convert("RGBA")
                    except Exception as conv_err:
                        st.error(f"SVG 转 PNG 时出错: {conv_err}")
                        return None
                else:
                    return Image.open(BytesIO(image_resp.content)).convert("RGBA")
            else:
                st.error(f"下载图像失败，状态码：{image_resp.status_code}")
        except Exception as download_err:
            st.error(f"请求图像时出错: {download_err}")
    else:
        st.error("未能从 API 响应中获取图像 URL。")
    return None

st.title("可自由拖动图案位置的个性化衣服定制")

# 1. 加载衬衫底图（使用相对路径）
shirt_path = "white_shirt.png"  # 改为相对路径
try:
    shirt_image = Image.open(shirt_path).convert("RGBA")
except Exception as e:
    st.error(f"无法加载衬衫图片：{e}")
    st.stop()

# 2. 在 session_state 中存储生成好的设计图
if "design_img" not in st.session_state:
    st.session_state["design_img"] = None

# 3. 用户输入个性化定制参数
st.subheader("请输入您的个性化定制需求：")
theme = st.text_input("主题或关键词 (必填)", "花卉图案")
style = st.text_input("设计风格 (如 abstract, cartoon, realistic 等)", "abstract")
colors = st.text_input("偏好颜色 (如 pink, gold, black)", "pink, gold")
details = st.text_area("更多细节 (如 swirling shapes, futuristic touches)", "some swirling shapes")

# 4. 生成设计图按钮：调用 generate_vector_image
if st.button("生成设计图"):
    if theme.strip():
        prompt_text = (
            f"Create a unique T-shirt design. "
            f"Theme: {theme}. "
            f"Style: {style}. "
            f"Colors: {colors}. "
            f"Details: {details}. "
            f"Make it visually appealing with transparent background."
        )
        with st.spinner("正在生成设计图..."):
            design_img = generate_vector_image(prompt_text)
        if design_img:
            st.session_state["design_img"] = design_img
            st.success("设计图已生成，请在下方画布上绘制矩形来放置图案。")
        else:
            st.error("设计图生成失败，请稍后重试。")
    else:
        st.warning("请至少输入主题或关键词！")

# 5. 显示画布，让用户用鼠标在衬衫上绘制矩形
st.write("在下方画布上 **绘制一个矩形**，表示图案要贴的位置和大小。")
# 直接传入 shirt_image（PIL 图像）作为背景图
canvas_result = st_canvas(
    fill_color="rgba(255, 255, 255, 0)",   # 透明填充
    stroke_width=3,
    stroke_color="red",
    background_image=shirt_image,
    update_streamlit=True,
    height=shirt_image.height,
    width=shirt_image.width,
    drawing_mode="rect",   # 仅允许绘制矩形
    key="canvas",
)

# 6. 叠加图案到衣服
if st.button("叠加图案到衣服"):
    if st.session_state["design_img"] is None:
        st.warning("请先生成设计图！")
    else:
        if canvas_result.json_data is not None:
            objects = canvas_result.json_data["objects"]
            if len(objects) == 0:
                st.warning("你尚未在画布上绘制任何矩形。")
            else:
                # 取最后一个绘制的矩形对象
                rect = objects[-1]
                left = int(rect["left"])
                top = int(rect["top"])
                width = int(rect["width"])
                height = int(rect["height"])

                # 从 session_state 获取设计图
                design_img = st.session_state["design_img"]
                # 将设计图缩放到矩形框的大小
                scaled_design = design_img.resize((width, height), Image.LANCZOS)

                # 将图案贴到衬衫底图
                composite = shirt_image.copy()
                try:
                    # 确保使用透明通道进行粘贴
                    composite.paste(scaled_design, (left, top), scaled_design)
                    st.image(composite, caption="最终定制效果", use_column_width=True)
                    
                    # 提供保存选项
                    if st.button("保存定制效果"):
                        save_path = "custom_tshirt.png"  # 改为相对路径
                        composite.save(save_path)
                        st.success(f"定制效果已保存至: {save_path}")
                except Exception as e:
                    st.error(f"粘贴图案时出现问题：{e}")
        else:
            st.warning("未检测到任何绘制数据。")
