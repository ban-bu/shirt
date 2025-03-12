import streamlit as st
from PIL import Image, ImageDraw
import requests
from io import BytesIO
import cairosvg
import base64
import numpy as np
import os

# 需要先安装: pip install streamlit-image-coordinates
from streamlit_image_coordinates import streamlit_image_coordinates

# ========== Deepbricks 配置信息 ==========
from openai import OpenAI
API_KEY = st.secrets["API_KEY"] if "API_KEY" in st.secrets else "YOUR_API_KEY"
BASE_URL = "https://api.deepbricks.ai/v1/"
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
# ==============================================

# 设置页面配置
st.set_page_config(
    page_title="个性化定制衣服生成系统",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        height: 3rem;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .design-area {
        border: 2px dashed #f63366;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 20px;
    }
    .highlight-text {
        color: #f63366;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def generate_vector_image(prompt):
    """根据提示词调用API生成图像"""
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

def draw_selection_box(image, start_point, end_point):
    """在图像上绘制选择框"""
    # Create a copy of the image to avoid modifying the original
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    
    # Ensure coordinates are properly formatted for rectangle drawing
    x1, y1 = start_point
    x2, y2 = end_point
    
    # Draw the outline with proper coordinates
    draw.rectangle(
        [(x1, y1), (x2, y2)],
        outline=(255, 0, 0),  # Red outline
        width=3
    )
    
    # Create a separate transparent overlay for the fill
    overlay = Image.new('RGBA', img_copy.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    
    # Draw the semi-transparent fill
    draw_overlay.rectangle(
        [(x1, y1), (x2, y2)],
        fill=(255, 0, 0, 50)  # Red with 50% transparency
    )
    
    # Ensure both images are in RGBA mode before compositing
    if img_copy.mode != 'RGBA':
        img_copy = img_copy.convert('RGBA')
    
    # Composite the images
    return Image.alpha_composite(img_copy, overlay)

def get_selection_coordinates(start_point, end_point):
    """获取选择框的坐标和尺寸"""
    x1, y1 = start_point
    x2, y2 = end_point
    
    # 确保坐标是从左上到右下
    left = min(x1, x2)
    top = min(y1, y2)
    right = max(x1, x2)
    bottom = max(y1, y2)
    
    width = right - left
    height = bottom - top
    
    return (left, top, width, height)

# 初始化会话状态
if 'start_point' not in st.session_state:
    st.session_state.start_point = None
if 'end_point' not in st.session_state:
    st.session_state.end_point = None
if 'selection_mode' not in st.session_state:
    st.session_state.selection_mode = False
if 'selection_areas' not in st.session_state:
    st.session_state.selection_areas = []
if 'base_image' not in st.session_state:
    st.session_state.base_image = None
if 'current_image' not in st.session_state:
    st.session_state.current_image = None
if 'generated_design' not in st.session_state:
    st.session_state.generated_design = None
if 'final_design' not in st.session_state:
    st.session_state.final_design = None

# 标题
st.title("👕 个性化定制衣服生成系统")
st.markdown("### 在T恤上直接选择区域，放置您的个性化设计")

# 创建两列布局
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("## 设计区域")
    
    # 加载衬衫底图
    if st.session_state.base_image is None:
        try:
            base_image = Image.open("white_shirt.png").convert("RGBA")
            st.session_state.base_image = base_image
            st.session_state.current_image = base_image.copy()
        except Exception as e:
            st.error(f"加载白衬衫图片时出错: {e}")
            st.stop()
    
    # 选择模式按钮
    if st.button("🖱️ " + ("退出选择模式" if st.session_state.selection_mode else "进入选择模式")):
        st.session_state.selection_mode = not st.session_state.selection_mode
        st.session_state.start_point = None
        st.session_state.end_point = None
    
    # 显示当前模式
    st.markdown(f"**当前模式:** {'<span class=\"highlight-text\">选择区域模式</span>' if st.session_state.selection_mode else '浏览模式'}", unsafe_allow_html=True)
    
    # 显示操作指南
    if st.session_state.selection_mode:
        st.info("👆 点击并拖动鼠标在T恤上选择一个区域，用于放置您的设计")
    
    # 显示当前图像并获取点击坐标
    current_image = st.session_state.current_image
    coordinates = streamlit_image_coordinates(
        current_image,
        key="shirt_image"
    )
    
    # 处理选择区域逻辑
    if st.session_state.selection_mode and coordinates:
        if st.session_state.start_point is None:
            st.session_state.start_point = (coordinates["x"], coordinates["y"])
        else:
            st.session_state.end_point = (coordinates["x"], coordinates["y"])
            
            # 绘制选择框
            if st.session_state.start_point and st.session_state.end_point:
                temp_image = st.session_state.base_image.copy()
                
                # 绘制已有的选择区域
                for area in st.session_state.selection_areas:
                    left, top, width, height = area
                    area_start = (left, top)
                    area_end = (left + width, top + height)
                    temp_image = draw_selection_box(temp_image, area_start, area_end)
                
                # 绘制当前选择区域
                temp_image = draw_selection_box(
                    temp_image, 
                    st.session_state.start_point, 
                    st.session_state.end_point
                )
                
                st.session_state.current_image = temp_image
                
                # 添加选择区域到列表
                selection = get_selection_coordinates(
                    st.session_state.start_point, 
                    st.session_state.end_point
                )
                st.session_state.selection_areas.append(selection)
                
                # 重置选择点
                st.session_state.start_point = None
                st.session_state.end_point = None
                
                # 刷新页面显示新的选择框
                st.experimental_rerun()
    
    # 显示已选择的区域数量
    if st.session_state.selection_areas:
        st.markdown(f"**已选择 {len(st.session_state.selection_areas)} 个区域**")
        
        # 清除选择按钮
        if st.button("🗑️ 清除所有选择区域"):
            st.session_state.selection_areas = []
            st.session_state.current_image = st.session_state.base_image.copy()
            st.experimental_rerun()

with col2:
    st.markdown("## 设计参数")
    
    # 用户输入个性化参数
    theme = st.text_input("主题或关键词 (必填)", "花卉图案")
    style = st.text_input("设计风格", "abstract")
    colors = st.text_input("偏好颜色", "pink, gold")
    details = st.text_area("更多细节", "some swirling shapes")
    
    # 生成设计按钮
    if st.button("🎨 生成设计"):
        if not theme.strip():
            st.warning("请至少输入主题或关键词！")
        elif not st.session_state.selection_areas:
            st.warning("请先在T恤上选择至少一个区域！")
        else:
            # 生成图案
            prompt_text = (
                f"Create a unique T-shirt design. "
                f"Theme: {theme}. "
                f"Style: {style}. "
                f"Colors: {colors}. "
                f"Details: {details}. "
                f"Make it visually appealing with transparent background."
            )
            
            with st.spinner("🔮 正在生成设计图..."):
                custom_design = generate_vector_image(prompt_text)
                
                if custom_design:
                    st.session_state.generated_design = custom_design
                    
                    # 在原图上合成
                    composite_image = st.session_state.base_image.copy()
                    
                    # 遍历所有选择区域，将设计图放置到每个区域
                    for area in st.session_state.selection_areas:
                        left, top, width, height = area
                        
                        # 将生成图案缩放到选择区域大小
                        if width > 0 and height > 0:  # 确保区域有效
                            scaled_design = custom_design.resize((width, height), Image.LANCZOS)
                            
                            try:
                                # 确保使用透明通道进行粘贴
                                composite_image.paste(scaled_design, (left, top), scaled_design)
                            except Exception as e:
                                st.warning(f"使用透明通道粘贴失败，直接粘贴: {e}")
                                composite_image.paste(scaled_design, (left, top))
                    
                    st.session_state.final_design = composite_image
                    st.experimental_rerun()
                else:
                    st.error("生成图像失败，请稍后重试。")

    # 显示生成的设计
    if st.session_state.generated_design is not None:
        st.markdown("### 生成的原始设计")
        st.image(st.session_state.generated_design, use_column_width=True)
    
    # 显示最终效果
    if st.session_state.final_design is not None:
        st.markdown("### 最终效果")
        st.image(st.session_state.final_design, use_column_width=True)
        
        # 提供下载选项
        buf = BytesIO()
        st.session_state.final_design.save(buf, format="PNG")
        buf.seek(0)
        st.download_button(
            label="💾 下载定制效果",
            data=buf,
            file_name="custom_tshirt.png",
            mime="image/png"
        )

# 页脚
st.markdown("---")
st.markdown("### 使用说明")
st.markdown("""
1. 点击"进入选择模式"按钮
2. 在T恤图片上点击并拖动鼠标选择区域
3. 可以选择多个区域
4. 填写设计参数
5. 点击"生成设计"按钮
6. 下载最终效果
""")
