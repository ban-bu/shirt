import streamlit as st
import warnings
warnings.filterwarnings('ignore')

from PIL import Image, ImageDraw
import requests
from io import BytesIO
import cairosvg
import base64
import numpy as np
import os
import pandas as pd
import uuid
import datetime
import json

# Requires installation: pip install streamlit-image-coordinates
from streamlit_image_coordinates import streamlit_image_coordinates

# ========== Deepbricks Configuration ==========
from openai import OpenAI
API_KEY = "sk-lNVAREVHjj386FDCd9McOL7k66DZCUkTp6IbV0u9970qqdlg"
BASE_URL = "https://api.deepbricks.ai/v1/"
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
# ==============================================

# Page configuration
st.set_page_config(
    page_title="AI Customized Clothing Consumer Behavior Experiment",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styles
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
    .purchase-intent {
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
    }
    .rating-container {
        display: flex;
        justify-content: space-between;
        margin: 20px 0;
    }
    .welcome-card {
        background-color: #f8f9fa;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 30px;
    }
    .group-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
        border: 1px solid #e0e0e0;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .group-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }
    .design-gallery {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 10px;
        margin: 20px 0;
    }
    .design-item {
        border: 2px solid transparent;
        border-radius: 5px;
        transition: border-color 0.2s;
        cursor: pointer;
    }
    .design-item.selected {
        border-color: #f63366;
    }
    .movable-box {
        cursor: move;
    }
</style>
""", unsafe_allow_html=True)

# Initialize data storage
DATA_FILE = "experiment_data.csv"

def initialize_experiment_data():
    """Initialize or load experiment data file"""
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            'user_id', 'experiment_group', 'timestamp', 'design_duration', 
            'age', 'gender', 'shopping_frequency', 'purchase_intent', 
            'satisfaction_score', 'customize_difficulty',
            'price_willing_to_pay', 'theme', 'design_choice', 'uniqueness_importance',
            'ai_attitude', 'feedback'
        ])
        df.to_csv(DATA_FILE, index=False)
    return True

def save_experiment_data(data):
    """Save experiment data to CSV file"""
    try:
        df = pd.read_csv(DATA_FILE)
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False

def generate_vector_image(prompt):
    """Generate an image based on the prompt"""
    try:
        resp = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard"
        )
    except Exception as e:
        st.error(f"Error calling API: {e}")
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
                        st.error(f"Error converting SVG to PNG: {conv_err}")
                        return None
                else:
                    return Image.open(BytesIO(image_resp.content)).convert("RGBA")
            else:
                st.error(f"Failed to download image, status code: {image_resp.status_code}")
        except Exception as download_err:
            st.error(f"Error requesting image: {download_err}")
    else:
        st.error("Could not get image URL from API response.")
    return None

def draw_selection_box(image, point=None):
    """Draw a fixed-size selection box on the image"""
    # Create a copy to avoid modifying the original image
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    
    # Fixed box size (1024 * 0.25)
    box_size = int(1024 * 0.25)
    
    # If no position is specified, place it in the center
    if point is None:
        x1 = (image.width - box_size) // 2
        y1 = (image.height - box_size) // 2
    else:
        x1, y1 = point
        # Ensure the selection box doesn't extend beyond image boundaries
        x1 = max(0, min(x1 - box_size//2, image.width - box_size))
        y1 = max(0, min(y1 - box_size//2, image.height - box_size))
    
    x2, y2 = x1 + box_size, y1 + box_size
    
    # Draw red outline
    draw.rectangle(
        [(x1, y1), (x2, y2)],
        outline=(255, 0, 0),
        width=2
    )
    
    # Create separate transparent overlay for fill
    overlay = Image.new('RGBA', img_copy.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    
    # Draw semi-transparent fill
    draw_overlay.rectangle(
        [(x1, y1), (x2, y2)],
        fill=(255, 0, 0, 50)
    )
    
    # Ensure both images are in RGBA mode
    if img_copy.mode != 'RGBA':
        img_copy = img_copy.convert('RGBA')
    
    # Composite images
    try:
        return Image.alpha_composite(img_copy, overlay), (x1, y1)
    except Exception as e:
        st.warning(f"Image composition failed: {e}")
        return img_copy, (x1, y1)

def get_selection_coordinates(point=None, image_size=None):
    """Get coordinates and dimensions of fixed-size selection box"""
    box_size = int(1024 * 0.25)
    
    if point is None and image_size is not None:
        width, height = image_size
        x1 = (width - box_size) // 2
        y1 = (height - box_size) // 2
    else:
        x1, y1 = point
        # Ensure selection box doesn't extend beyond image boundaries
        if image_size:
            width, height = image_size
            x1 = max(0, min(x1 - box_size//2, width - box_size))
            y1 = max(0, min(y1 - box_size//2, height - box_size))
    
    return (x1, y1, box_size, box_size)

def match_background_to_shirt(design_image, shirt_image):
    """Adjust design image background color to match shirt"""
    # Ensure images are in RGBA mode
    design_image = design_image.convert("RGBA")
    shirt_image = shirt_image.convert("RGBA")
    
    # Get shirt background color (assuming top-left corner color)
    shirt_bg_color = shirt_image.getpixel((0, 0))
    
    # Get design image data
    datas = design_image.getdata()
    newData = []
    
    for item in datas:
        # If pixel is transparent, keep it unchanged
        if item[3] == 0:
            newData.append(item)
        else:
            # Adjust non-transparent pixel background color to match shirt
            newData.append((shirt_bg_color[0], shirt_bg_color[1], shirt_bg_color[2], item[3]))
    
    design_image.putdata(newData)
    return design_image

# Preset design options (using local images)
PRESET_DESIGNS = {
    "Floral Pattern": "preset_designs/floral.png",
    "Geometric Pattern": "preset_designs/geometric.png",
    "Abstract Art": "preset_designs/abstract.png",
    "Minimalist Lines": "preset_designs/minimalist.png",
    "Animal Pattern": "preset_designs/animal.png"
}

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = "welcome"
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()
if 'experiment_group' not in st.session_state:
    st.session_state.experiment_group = None
if 'base_image' not in st.session_state:
    st.session_state.base_image = None
if 'current_image' not in st.session_state:
    st.session_state.current_image = None
if 'current_box_position' not in st.session_state:
    st.session_state.current_box_position = None
if 'generated_design' not in st.session_state:
    st.session_state.generated_design = None
if 'final_design' not in st.session_state:
    st.session_state.final_design = None
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'selected_preset' not in st.session_state:
    st.session_state.selected_preset = None

# Ensure data file exists
initialize_experiment_data()

# Welcome and information collection page
def show_welcome_page():
    st.title("👕 AI Customized Clothing Consumer Behavior Experiment")
    
    with st.container():
        st.markdown('<div class="welcome-card">', unsafe_allow_html=True)
        st.markdown("### Welcome to our experiment!")
        st.markdown("""
        This experiment aims to study the impact of different clothing customization methods on consumer purchasing behavior. You will have the opportunity to experience the T-shirt customization process and share your feedback.
        
        **Experiment Process**:
        1. Fill in your basic information
        2. Choose an experiment group
        3. Complete T-shirt customization
        4. Submit survey feedback
        
        Your participation is crucial to our research. Thank you for your support!
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### Please fill in your basic information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        age = st.number_input("Your age", min_value=18, max_value=80, value=25)
        
        gender = st.radio("Your gender", 
                          options=["Male", "Female", "Other", "Prefer not to say"])
    
    with col2:
        shopping_frequency = st.selectbox(
            "How often do you purchase clothing?",
            options=["Weekly", "Several times a month", "Quarterly", "Several times a year", "Rarely"]
        )
        
        customize_experience = st.selectbox(
            "Have you had any clothing customization experience before?",
            options=["Extensive experience", "Some experience", "Little experience", "No experience"]
        )
    
    ai_attitude = st.slider(
        "What is your attitude toward artificial intelligence technology?",
        min_value=1, max_value=10, value=5,
        help="1 means very negative, 10 means very positive"
    )
    
    uniqueness_importance = st.slider(
        "How important is clothing uniqueness to you?",
        min_value=1, max_value=10, value=5,
        help="1 means not important at all, 10 means very important"
    )
    
    st.markdown("### Please select the experiment group you want to participate in")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="group-card">', unsafe_allow_html=True)
        st.markdown("#### AI Customization Group")
        st.markdown("""
        - Use artificial intelligence technology to generate custom patterns
        - Create unique designs based on your preferences and descriptions
        - Freely place design patterns on the T-shirt
        """)
        if st.button("Choose AI Customization Group"):
            st.session_state.experiment_group = "AI Customization Group"
            st.session_state.user_info = {
                'age': age,
                'gender': gender,
                'shopping_frequency': shopping_frequency,
                'customize_experience': customize_experience,
                'ai_attitude': ai_attitude,
                'uniqueness_importance': uniqueness_importance
            }
            st.session_state.page = "design"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="group-card">', unsafe_allow_html=True)
        st.markdown("#### Preset Design Group")
        st.markdown("""
        - Choose patterns from a curated design library
        - High-quality professional designs
        - Freely place selected patterns on the T-shirt
        """)
        if st.button("Choose Preset Design Group"):
            st.session_state.experiment_group = "Preset Design Group"
            st.session_state.user_info = {
                'age': age,
                'gender': gender,
                'shopping_frequency': shopping_frequency,
                'customize_experience': customize_experience,
                'ai_attitude': ai_attitude,
                'uniqueness_importance': uniqueness_importance
            }
            st.session_state.page = "design"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Admin area - Experiment data analysis (password protected)
    st.markdown("---")
    with st.expander("Experiment Data Analysis (Admin Only)"):
        admin_password = st.text_input("Admin Password", type="password")
        if admin_password == "admin123":  # Simple password example, use more secure authentication in actual applications
            try:
                # Read experiment data
                experiment_df = pd.read_csv(DATA_FILE)
                
                if not experiment_df.empty:
                    st.markdown("### Experiment Data Statistics")
                    
                    # Basic statistics
                    st.markdown("#### Participant Statistics")
                    group_counts = experiment_df['experiment_group'].value_counts()
                    st.write(f"Total participants: {len(experiment_df)}")
                    st.write(f"AI Customization Group: {group_counts.get('AI Customization Group', 0)} people")
                    st.write(f"Preset Design Group: {group_counts.get('Preset Design Group', 0)} people")
                    
                    # Purchase intention comparison
                    st.markdown("#### Purchase Intention Comparison")
                    purchase_by_group = experiment_df.groupby('experiment_group')['purchase_intent'].mean()
                    st.bar_chart(purchase_by_group)
                    
                    # Satisfaction comparison
                    st.markdown("#### Satisfaction Comparison")
                    satisfaction_by_group = experiment_df.groupby('experiment_group')['satisfaction_score'].mean()
                    st.bar_chart(satisfaction_by_group)
                    
                    # Willing to pay price comparison
                    st.markdown("#### Willing to Pay Price Comparison")
                    price_by_group = experiment_df.groupby('experiment_group')['price_willing_to_pay'].mean()
                    st.bar_chart(price_by_group)
                    
                    # Export data button
                    st.download_button(
                        label="Export Complete Data (CSV)",
                        data=experiment_df.to_csv(index=False).encode('utf-8'),
                        file_name="experiment_data_export.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No experiment data yet, please wait for user participation.")
            except Exception as e:
                st.error(f"Error loading or analyzing data: {e}")
        elif admin_password:
            st.error("Incorrect password, unable to access admin area.")

# AI Customization Group design page
def show_ai_design_page():
    st.title("👕 AI Customization Experiment Platform")
    st.markdown("### AI Customization Group - Create Your Unique T-shirt Design")
    
    # Create two-column layout
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("## Design Area")
    
        # Load T-shirt base image
        if st.session_state.base_image is None:
            try:
                base_image = Image.open("white_shirt.png").convert("RGBA")
                st.session_state.base_image = base_image
                # Initialize by drawing selection box in the center
                initial_image, initial_pos = draw_selection_box(base_image)
                st.session_state.current_image = initial_image
                st.session_state.current_box_position = initial_pos
            except Exception as e:
                st.error(f"Error loading white T-shirt image: {e}")
                st.stop()
    
        st.markdown("**👇 Click anywhere on the T-shirt to move the design frame**")
        
        # Display current image and get click coordinates
        current_image = st.session_state.current_image
        coordinates = streamlit_image_coordinates(
            current_image,
            key="shirt_image"
        )
    
        # Handle selection area logic - simplify to directly move red box
        if coordinates:
            # Update selection box at current mouse position
            current_point = (coordinates["x"], coordinates["y"])
            temp_image, new_pos = draw_selection_box(st.session_state.base_image, current_point)
            st.session_state.current_image = temp_image
            st.session_state.current_box_position = new_pos
            st.rerun()
    
    with col2:
        st.markdown("## Design Parameters")
        
        # User input for personalization parameters
        theme = st.text_input("Theme or keyword (required)", "Floral pattern")
        style = st.text_input("Design style", "abstract")
        colors = st.text_input("Preferred colors", "pink, gold")
        details = st.text_area("Additional details", "some swirling shapes")
        
        # Generate design button
        if st.button("🎨 Generate AI Design"):
            if not theme.strip():
                st.warning("Please enter at least a theme or keyword!")
            else:
                # Generate pattern
                prompt_text = (
                        f"Create a decorative pattern with a completely transparent background. "
                    f"Theme: {theme}. "
                    f"Style: {style}. "
                    f"Colors: {colors}. "
                    f"Details: {details}. "
                        f"The pattern must have NO background, ONLY the design elements on transparency. "
                        f"The output must be PNG with alpha channel transparency."
                )
                
                with st.spinner("🔮 Generating design..."):
                    custom_design = generate_vector_image(prompt_text)
                    
                    if custom_design:
                        st.session_state.generated_design = custom_design
                        
                        # Composite on the original image
                        composite_image = st.session_state.base_image.copy()
                        
                        # Place design at current selection position
                        left, top = st.session_state.current_box_position
                        box_size = int(1024 * 0.25)
                        
                        # Scale generated pattern to selection area size
                        scaled_design = custom_design.resize((box_size, box_size), Image.LANCZOS)
                        
                        try:
                            # Ensure transparency channel is used for pasting
                            composite_image.paste(scaled_design, (left, top), scaled_design)
                        except Exception as e:
                            st.warning(f"Transparent channel paste failed, direct paste: {e}")
                            composite_image.paste(scaled_design, (left, top))
                        
                        st.session_state.final_design = composite_image
                        st.rerun()
                    else:
                        st.error("Failed to generate image, please try again later.")
    
    # Display final effect - move out of col2, place at bottom of overall page
    if st.session_state.final_design is not None:
        st.markdown("### Final Result")
        st.image(st.session_state.final_design, use_container_width=True)  # Use new parameter
        
        # Provide download option
        col1, col2 = st.columns(2)
        with col1:
            buf = BytesIO()
            st.session_state.final_design.save(buf, format="PNG")
            buf.seek(0)
            st.download_button(
                label="💾 Download Custom Design",
                data=buf,
                file_name="custom_tshirt.png",
                mime="image/png"
            )
        
        with col2:
            # Confirm completion button
            if st.button("Confirm Completion"):
                st.session_state.page = "survey"
                st.rerun()
    
    # Return to main interface button - modified here
    if st.button("Return to Main Page"):
        # Clear all design-related states
        st.session_state.base_image = None
        st.session_state.current_image = None
        st.session_state.current_box_position = None
        st.session_state.generated_design = None
        st.session_state.final_design = None
        # Only change page state, retain user info and experiment group
        st.session_state.page = "welcome"
        st.rerun()

# Preset Design Group design page
def show_preset_design_page():
    st.title("👕 预制设计实验平台")
    st.markdown("### 预制设计组 - 自定义您的T恤")
    
    # 创建两列布局
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("## 设计区域")
        
        # 加载T恤基础图像
        if st.session_state.base_image is None:
            try:
                base_image = Image.open("white_shirt.png").convert("RGBA")
                st.session_state.base_image = base_image
                st.session_state.original_base_image = base_image.copy()  # 保存原始白色T恤图像
                # 初始化，在中心绘制选择框
                initial_image, initial_pos = draw_selection_box(base_image)
                st.session_state.current_image = initial_image
                st.session_state.current_box_position = initial_pos
            except Exception as e:
                st.error(f"加载白色T恤图像时出错: {e}")
                st.stop()
        
        st.markdown("**👇 点击T恤上的任意位置移动设计框或直接绘画**")
        
        # 显示当前图像并获取点击坐标
        current_image = st.session_state.current_image
        coordinates = streamlit_image_coordinates(
            current_image,
            key="shirt_image"
        )
        
        # 处理选择区域逻辑或绘画逻辑
        if coordinates:
            # 如果处于绘画模式
            if 'drawing_mode' in st.session_state and st.session_state.drawing_mode:
                # 在T恤上绘画
                if 'drawn_points' not in st.session_state:
                    st.session_state.drawn_points = []
                
                st.session_state.drawn_points.append((coordinates["x"], coordinates["y"]))
                
                # 在当前图像上绘制点
                draw_img = st.session_state.current_image.copy()
                draw = ImageDraw.Draw(draw_img)
                
                # 获取绘画颜色和大小
                draw_color = st.session_state.get('draw_color', (255, 0, 0, 255))
                brush_size = st.session_state.get('brush_size', 5)
                
                # 绘制所有点
                for point in st.session_state.drawn_points:
                    draw.ellipse(
                        [(point[0]-brush_size, point[1]-brush_size), 
                         (point[0]+brush_size, point[1]+brush_size)], 
                        fill=draw_color
                    )
                
                st.session_state.current_image = draw_img
                st.rerun()
            else:
                # 移动选择框
                current_point = (coordinates["x"], coordinates["y"])
                # 获取当前T恤图像
                base_img = st.session_state.base_image.copy()
                temp_image, new_pos = draw_selection_box(base_img, current_point)
                st.session_state.current_image = temp_image
                st.session_state.current_box_position = new_pos
                st.rerun()

    with col2:
        st.markdown("## 自定义选项")
        
        # 绘画模式选项
        st.markdown("### 直接绘画选项")
        drawing_mode = st.checkbox("启用绘画模式", value=False)
        st.session_state.drawing_mode = drawing_mode
        
        color_options = {
            "黑色": (0, 0, 0),
            "红色": (255, 0, 0),
            "蓝色": (0, 0, 255),
            "绿色": (0, 128, 0),
            "黄色": (255, 255, 0),
            "粉色": (255, 192, 203),
            "紫色": (128, 0, 128)
        }
        
        if drawing_mode:
            # 绘画设置
            draw_color_name = st.selectbox(
                "绘画颜色",
                options=list(color_options.keys()),
                index=0  # 默认黑色
            )
            st.session_state.draw_color = color_options[draw_color_name] + (255,)  # 添加alpha通道
            
            st.session_state.brush_size = st.slider("笔刷大小", 1, 20, 5)
            
            if st.button("清除绘画"):
                if 'drawn_points' in st.session_state:
                    st.session_state.drawn_points = []
                # 重置当前图像
                current_point = st.session_state.current_box_position
                temp_image, _ = draw_selection_box(st.session_state.base_image, current_point)
                st.session_state.current_image = temp_image
                st.rerun()
        else:
            # 预制设计选择
            st.markdown("### 选择预制设计")
            
            # 获取预设设计文件夹中的所有图像
            predesign_folder = "predesign"
            design_files = []
            
            # 确保文件夹存在
            if not os.path.exists(predesign_folder):
                st.error(f"预制设计文件夹未找到: {predesign_folder}，请确保它存在。")
            else:
                # 获取所有支持的图像文件
                for file in os.listdir(predesign_folder):
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        design_files.append(file)
                
                if not design_files:
                    st.warning(f"{predesign_folder} 文件夹中未找到图像文件。")
                else:
                    # 显示图像选择界面
                    selected_file = st.radio(
                        "可用设计",
                        options=design_files,
                        horizontal=True
                    )
                    
                    st.session_state.selected_preset = selected_file
                    
                    # 显示选定的设计
                    if st.session_state.selected_preset:
                        try:
                            # 加载设计图像
                            design_path = os.path.join(predesign_folder, selected_file)
                            preset_design = Image.open(design_path).convert("RGBA")
                            st.image(preset_design, caption=f"预制设计: {selected_file}", use_container_width=True)
                            
                            # 应用设计按钮
                            if st.button("应用到T恤"):
                                st.session_state.generated_design = preset_design
                                
                                # 合成到原始图像
                                composite_image = st.session_state.base_image.copy()
                                
                                # 在当前选择位置放置设计
                                left, top = st.session_state.current_box_position
                                box_size = int(1024 * 0.25)
                                
                                # 将预设图案缩放到选择区域大小
                                scaled_design = preset_design.resize((box_size, box_size), Image.LANCZOS)
                                
                                try:
                                    # 确保透明通道用于粘贴
                                    composite_image.paste(scaled_design, (left, top), scaled_design)
                                except Exception as e:
                                    st.warning(f"透明通道粘贴失败，直接粘贴: {e}")
                                    composite_image.paste(scaled_design, (left, top))
                            
                                st.session_state.final_design = composite_image
                                st.rerun()
                        except Exception as e:
                            st.error(f"处理预制设计时出错: {e}")
    
    # 显示最终效果 - 保持与AI自定义页面一致的布局
    if st.session_state.final_design is not None:
        st.markdown("### 最终效果")
        st.image(st.session_state.final_design, use_container_width=True)
        
        # 提供下载选项
        col1, col2 = st.columns(2)
        with col1:
            buf = BytesIO()
            st.session_state.final_design.save(buf, format="PNG")
            buf.seek(0)
            st.download_button(
                label="💾 下载自定义设计",
                data=buf,
                file_name="custom_tshirt.png",
                mime="image/png"
            )
        
        with col2:
            # 确认完成按钮，导航到问卷调查页面
            if st.button("确认完成"):
                st.session_state.page = "survey"
                st.rerun()
    
    # 返回主界面按钮
    if st.button("返回主页"):
        # 清除所有设计相关状态
        st.session_state.base_image = None
        st.session_state.current_image = None
        st.session_state.current_box_position = None
        st.session_state.generated_design = None
        st.session_state.final_design = None
        st.session_state.selected_preset = None  # 清除选定的预制设计
        if 'drawing_mode' in st.session_state:
            del st.session_state.drawing_mode
        if 'drawn_points' in st.session_state:
            del st.session_state.drawn_points
        if 'original_base_image' in st.session_state:
            del st.session_state.original_base_image
        # 只改变页面状态，保留用户信息和实验组
        st.session_state.page = "welcome"
        st.rerun()

# Survey page
def show_survey_page():
    st.title("👕 Clothing Customization Experiment Survey")
    st.markdown(f"### {st.session_state.experiment_group} - Your Feedback")
    
    if not st.session_state.submitted:
        st.markdown('<div class="purchase-intent">', unsafe_allow_html=True)
        
        # Calculate time spent on design
        design_duration = (datetime.datetime.now() - st.session_state.start_time).total_seconds() / 60
        
        # Purchase intention
        purchase_intent = st.slider(
            "If this T-shirt were sold in the market, how likely would you be to purchase it?",
            min_value=1, max_value=10, value=5,
            help="1 means definitely would not buy, 10 means definitely would buy"
        )
        
        # Satisfaction rating
        satisfaction_score = st.slider(
            "How satisfied are you with the final design result?",
            min_value=1, max_value=10, value=5,
            help="1 means very dissatisfied, 10 means very satisfied"
        )
        
        # Different questions for different groups
        if st.session_state.experiment_group == "AI Customization Group":
            # AI customization group specific questions
            ai_effectiveness = st.slider(
                "How well does the AI-generated design meet your expectations?",
                min_value=1, max_value=10, value=5,
                help="1 means not at all, 10 means completely meets expectations"
            )
            
            ai_uniqueness = st.slider(
                "How unique do you think the AI-generated design is?",
                min_value=1, max_value=10, value=5,
                help="1 means not at all unique, 10 means very unique"
            )
            
            ai_experience = st.radio(
                "How does the AI customization experience compare to your previous shopping experiences?",
                options=["Better", "About the same", "Worse", "Cannot compare"]
            )
            
            ai_future = st.radio(
                "Would you consider using AI customization for clothing in the future?",
                options=["Definitely", "Probably", "Probably not", "Definitely not"]
            )
        else:
            # Preset design group specific questions
            design_variety = st.slider(
                "How satisfied are you with the variety of preset designs?",
                min_value=1, max_value=10, value=5,
                help="1 means very dissatisfied, 10 means very satisfied"
            )
            
            design_quality = st.slider(
                "How would you rate the quality of the selected design?",
                min_value=1, max_value=10, value=5,
                help="1 means very poor quality, 10 means excellent quality"
            )
            
            design_preference = st.radio(
                "Which type of clothing design do you prefer?",
                options=["Popular mainstream styles", "Rare unique designs", "Personalized custom designs", "Simple basic styles"]
            )
            
            design_limitation = st.radio(
                "Did you feel the preset designs limited your creative expression?",
                options=["Very limiting", "Somewhat limiting", "Barely limiting", "Not limiting at all"]
            )
        
        # Common questions for both groups
        customize_difficulty = st.slider(
            "How difficult was it to customize a T-shirt using this system?",
            min_value=1, max_value=10, value=5,
            help="1 means very difficult, 10 means very easy"
        )
        
        # Willing to pay price
        price_willing_to_pay = st.slider(
            "How much would you be willing to pay for this customized T-shirt (in USD)?",
            min_value=0, max_value=100, value=20, step=5
        )
        
        # Open-ended feedback
        feedback = st.text_area(
            "Please share any other feedback or suggestions about this customization experience",
            height=100
        )
        
        # Submit button
        if st.button("Submit Feedback"):
            # Collect all data
            experiment_data = {
                'user_id': st.session_state.user_id,
                'experiment_group': st.session_state.experiment_group,
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'design_duration': round(design_duration, 2),
                'age': st.session_state.user_info.get('age'),
                'gender': st.session_state.user_info.get('gender'),
                'shopping_frequency': st.session_state.user_info.get('shopping_frequency'),
                'purchase_intent': purchase_intent,
                'satisfaction_score': satisfaction_score,
                'customize_difficulty': customize_difficulty,
                'price_willing_to_pay': price_willing_to_pay,
                'theme': st.session_state.selected_preset if st.session_state.experiment_group == "Preset Design Group" else None,
                'design_choice': st.session_state.selected_preset if st.session_state.experiment_group == "Preset Design Group" else None,
                'uniqueness_importance': st.session_state.user_info.get('uniqueness_importance'),
                'ai_attitude': st.session_state.user_info.get('ai_attitude'),
                'feedback': feedback
            }
            
            # Add group-specific data
            if st.session_state.experiment_group == "AI Customization Group":
                experiment_data.update({
                    'ai_effectiveness': ai_effectiveness,
                    'ai_uniqueness': ai_uniqueness,
                    'ai_experience': ai_experience,
                    'ai_future': ai_future
                })
            else:
                experiment_data.update({
                    'design_variety': design_variety,
                    'design_quality': design_quality,
                    'design_preference': design_preference,
                    'design_limitation': design_limitation
                })
            
            # Save data
            if save_experiment_data(experiment_data):
                st.session_state.submitted = True
                st.success("Thank you for your feedback! Your data has been recorded and will help our research.")
                st.rerun()
            else:
                st.error("Failed to save feedback data, please try again.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.success("You have successfully submitted the survey! Thank you for your participation.")
        
        if st.button("Return to Main Page"):
            # Reset session state, retain user ID and experiment data
            design_keys = [
                'base_image', 'current_image', 'current_box_position', 
                'generated_design', 'final_design', 'selected_preset',
                'page', 'experiment_group', 'submitted', 'start_time'
            ]
            for key in design_keys:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Reinitialize necessary states
            st.session_state.page = "welcome"
            st.session_state.start_time = datetime.datetime.now()
            st.session_state.submitted = False
            st.rerun()

# Main program control logic
def main():
    # Initialize data file
    initialize_experiment_data()
    
    # Display different content based on current page
    if st.session_state.page == "welcome":
        show_welcome_page()
    elif st.session_state.page == "design":
        if st.session_state.experiment_group == "AI Customization Group":
            show_ai_design_page()
        elif st.session_state.experiment_group == "Preset Design Group":
            show_preset_design_page()
        else:
            st.error("Experiment group type error, please return to the home page and select again")
            if st.button("Return to Home Page"):
                st.session_state.page = "welcome"
                st.rerun()
    elif st.session_state.page == "survey":
        show_survey_page()

# Run application
if __name__ == "__main__":
    main()
