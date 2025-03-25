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

# 在导入部分添加以下内容
from streamlit.components.v1 import html

# 安装：pip install streamlit-drawable-canvas
from streamlit_drawable_canvas import st_canvas

# ========== Deepbricks Configuration ==========
from openai import OpenAI
API_KEY = "sk-lNVAREVHjj386FDCd9McOL7k66DZCUkTp6IbV0u9970qqdlg"
BASE_URL = "https://api.deepbricks.ai/v1/"
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
# ==============================================

# Page configuration
st.set_page_config(
    page_title="AI Co-Creation Clothing Consumer Behavior Experiment",
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
if 'preset_design' not in st.session_state:
    st.session_state.preset_design = None
if 'drawn_design' not in st.session_state:
    st.session_state.drawn_design = None
if 'preset_position' not in st.session_state:
    st.session_state.preset_position = (0, 0)  # 默认居中，表示相对红框左上角的偏移
if 'preset_scale' not in st.session_state:
    st.session_state.preset_scale = 40  # 默认为40%
if 'design_mode' not in st.session_state:
    st.session_state.design_mode = "preset"  # 默认使用预设设计模式

# Ensure data file exists
initialize_experiment_data()

# Welcome and information collection page
def show_welcome_page():
    st.title("👕 AI Co-Creation Clothing Consumer Behavior Experiment")
    
    with st.container():
        st.markdown('<div class="welcome-card">', unsafe_allow_html=True)
        st.markdown("### Welcome to our experiment!")
        st.markdown("""
        This experiment aims to study the impact of AI Co-Creation on consumer purchasing behavior. You will have the opportunity to experience the T-shirt customization process and share your feedback.
        
        **Experiment Process**:
        1. Choose an experiment group
        2. Complete T-shirt customization
        3. Submit survey feedback
        
        Your participation is crucial to our research. Thank you for your support!
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
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
                'age': 25,  # 默认值
                'gender': "Male",  # 默认值
                'shopping_frequency': "Weekly",  # 默认值
                'customize_experience': "Some experience",  # 默认值
                'ai_attitude': 5,  # 默认值
                'uniqueness_importance': 5  # 默认值
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
                'age': 25,  # 默认值
                'gender': "Male",  # 默认值
                'shopping_frequency': "Weekly",  # 默认值
                'customize_experience': "Some experience",  # 默认值
                'ai_attitude': 5,  # 默认值
                'uniqueness_importance': 5  # 默认值
            }
            st.session_state.page = "design"
            st.rerun()

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
    st.title("👕 AI Co-Creation Experiment Platform")
    st.markdown("### AI Co-Creation Group - Create Your Unique T-shirt Design")
    
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
        
        # User input for personalization parameters - improved prompts and defaults
        theme = st.text_input("Theme or keyword (required)", "Elegant floral pattern")
        
        # Add style selection dropdown with more professional style options
        style_options = [
            "Watercolor style", "Sketch style", "Geometric shapes", "Minimalist", 
            "Vintage style", "Pop art", "Japanese style", "Nordic design",
            "Classical ornament", "Digital illustration", "Abstract art", "Ethnic motifs"
        ]
        style = st.selectbox("Design style", style_options, index=0)
        
        # Improved color selection
        color_scheme_options = [
            "Soft warm tones (pink, gold, light orange)",
            "Fresh cool tones (blue, mint, white)",
            "Nature colors (green, brown, beige)",
            "Bright and vibrant (red, yellow, orange)",
            "Elegant deep tones (navy, purple, dark green)",
            "Black and white contrast",
            "Colorful mix",
            "Custom colors"
        ]
        color_scheme = st.selectbox("Color scheme", color_scheme_options)
        
        # If custom colors are selected, show input field
        if color_scheme == "Custom colors":
            colors = st.text_input("Enter desired colors (comma separated)", "pink, gold, sky blue")
        else:
            # Set corresponding color values based on selected scheme
            color_mapping = {
                "Soft warm tones (pink, gold, light orange)": "pink, gold, light orange, cream",
                "Fresh cool tones (blue, mint, white)": "sky blue, mint green, white, light gray",
                "Nature colors (green, brown, beige)": "forest green, brown, beige, olive",
                "Bright and vibrant (red, yellow, orange)": "bright red, yellow, orange, lemon yellow",
                "Elegant deep tones (navy, purple, dark green)": "navy blue, violet, dark green, burgundy",
                "Black and white contrast": "black, white, gray",
                "Colorful mix": "red, blue, yellow, green, purple, orange"
            }
            colors = color_mapping[color_scheme]
        
        # Improved design details options
        details_options = [
            "Fine outlines and lines",
            "Smooth gradient effects",
            "Floral and plant elements",
            "Geometric shapes and patterns",
            "Waves and curves",
            "Dotted textures",
            "Repeating patterns",
            "Randomly distributed elements",
            "Custom details"
        ]
        details_type = st.selectbox("Detail type", details_options)
        
        if details_type == "Custom details":
            details = st.text_area("Describe desired design details", "Elegant curves and swirling shapes")
        else:
            # Preset detail descriptions
            details_mapping = {
                "Fine outlines and lines": "Design includes fine outlines and smooth lines, highlighting the shape and contours of the pattern.",
                "Smooth gradient effects": "Design uses smooth color gradients, elegantly transitioning from one color to another.",
                "Floral and plant elements": "Design incorporates delicate flowers, leaves and other plant elements with a natural organic feel.",
                "Geometric shapes and patterns": "Design uses clean geometric shapes like triangles, circles, squares arranged in attractive patterns.",
                "Waves and curves": "Design incorporates flowing waves and elegant curves creating a sense of movement and rhythm.",
                "Dotted textures": "Design uses dot patterns to create texture and depth, similar to pointillism technique.",
                "Repeating patterns": "Design contains regularly repeating elements forming a unified, harmonious pattern.",
                "Randomly distributed elements": "Elements in the design are randomly distributed, creating a natural, irregular appearance."
            }
            details = details_mapping[details_type]
        
        # Add design complexity option
        complexity = st.slider("Design complexity", 1, 10, 5, 
                              help="1 means very simple, 10 means very complex")
        
        # Automatically set detail level based on complexity
        detail_level = "low" if complexity <= 3 else "medium" if complexity <= 7 else "high"
        
        # Improved design generation button
        if st.button("🎨 Generate AI Design"):
            if not theme.strip():
                st.warning("Please enter at least a theme or keyword!")
            else:
                # Generate more professional and detailed prompt text
                prompt_text = (
                    f"Design a pattern with '{theme}' theme using {style}. "
                    f"Use the following colors: {colors}. "
                    f"Design details: {details}. "
                    f"Design complexity is {complexity}/10 with {detail_level} level of detail. "
                    f"The pattern should have an attractive, balanced composition suitable for clothing print. "
                    f"Create a PNG format image with transparent background, ensuring only the design elements are visible with no background. "
                    f"The design style should be professional and modern, appropriate for clothing prints. "
                    f"Ensure the pattern has crisp edges and a high-quality appearance. "
                    f"The output must be PNG with alpha channel transparency."
                )
                
                with st.spinner("🔮 Generating design... please wait"):
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
        
        # 添加清空设计按钮
        if st.button("🗑️ Clear All Designs", key="clear_designs"):
            # 清空所有设计相关的状态变量
            st.session_state.generated_design = None
            # 重置最终设计为基础T恤图像
            st.session_state.final_design = None
            # 重置当前图像为带选择框的基础图像
            temp_image, _ = draw_selection_box(st.session_state.base_image, st.session_state.current_box_position)
            st.session_state.current_image = temp_image
            st.rerun()
        
        st.image(st.session_state.final_design, use_container_width=True)
        
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
    st.title("👕 Preset Design Experiment Platform")
    st.markdown("### Preset Design Group - Choose Your Favorite T-shirt Design")
    
    # 创建两列布局：左侧T恤区域，右侧设计选择区域
    design_area_col, options_col = st.columns([3, 2])
    
    with design_area_col:
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
        
        # 初始化临时设计变量（如果需要）
        if 'temp_preset_design' not in st.session_state:
            st.session_state.temp_preset_design = None
        if 'temp_preset_position' not in st.session_state:
            st.session_state.temp_preset_position = (0, 0)
        if 'temp_preset_scale' not in st.session_state:
            st.session_state.temp_preset_scale = 40
        if 'design_mode' not in st.session_state:
            st.session_state.design_mode = "preset"  # 默认使用预设设计模式
            
        # 准备显示的图像（带有预览效果）
        display_image = st.session_state.current_image.copy()
        
        # 如果有临时预设设计且正在调整位置，直接在红框中显示预览
        if st.session_state.temp_preset_design is not None and st.session_state.design_mode == "preset":
            # 在当前图像上绘制预览
            display_image = draw_design_preview(
                display_image,
                st.session_state.temp_preset_design,
                st.session_state.current_box_position,
                st.session_state.temp_preset_position,
                st.session_state.temp_preset_scale
            )
        
        # Display current image and get click coordinates
        coordinates = streamlit_image_coordinates(
            display_image,
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

        # 显示最终设计结果（如果有）
        if st.session_state.final_design is not None:
            st.markdown("### Final Result")
            
            # 修改清空设计按钮
            if st.button("🗑️ Clear All Designs", key="clear_designs"):
                # 保存当前红框位置
                current_left, current_top = st.session_state.current_box_position
                box_size = int(1024 * 0.25)
                
                # 计算红框中心点坐标
                center_x = current_left + box_size // 2
                center_y = current_top + box_size // 2
                
                # 清空所有设计相关的状态变量
                st.session_state.preset_design = None
                st.session_state.drawn_design = None
                st.session_state.temp_preset_design = None
                st.session_state.preset_position = (0, 0)
                st.session_state.preset_scale = 40
                # 重置最终设计为基础T恤图像
                st.session_state.final_design = None
                
                # 使用中心点坐标重新绘制选择框
                temp_image, new_pos = draw_selection_box(st.session_state.base_image, (center_x, center_y))
                st.session_state.current_image = temp_image
                st.session_state.current_box_position = new_pos
                st.rerun()
            
            st.image(st.session_state.final_design, use_container_width=True)
            
            # Provide download and completion options
            download_col, complete_col = st.columns(2)
            with download_col:
                buf = BytesIO()
                st.session_state.final_design.save(buf, format="PNG")
                buf.seek(0)
                st.download_button(
                    label="💾 Download Custom Design",
                    data=buf,
                    file_name="custom_tshirt.png",
                    mime="image/png"
                )
            
            with complete_col:
                # Add confirm completion button that navigates to the survey page
                if st.button("Confirm Completion"):
                    st.session_state.page = "survey"
                    st.rerun()

    # 设计选择区域
    with options_col:
        st.markdown("## Design Options")
        
        # 添加设计模式选择
        design_mode = st.radio(
            "Choose design method:",
            options=["Use preset design", "Draw your own design"],
            horizontal=True,
            index=0 if st.session_state.design_mode == "preset" else 1
        )
        
        # 更新设计模式
        if (design_mode == "Use preset design" and st.session_state.design_mode != "preset") or \
           (design_mode == "Draw your own design" and st.session_state.design_mode != "draw"):
            st.session_state.design_mode = "preset" if design_mode == "Use preset design" else "draw"
            st.rerun()
        
        # 根据当前设计模式显示相应的界面
        if st.session_state.design_mode == "preset":
            # 预设设计选择界面
            st.markdown("## Preset Design Selection")
            
            # Get all images from predesign folder
            predesign_folder = "predesign"
            design_files = []
            
            # Ensure folder exists
            if not os.path.exists(predesign_folder):
                st.error(f"Preset design folder not found: {predesign_folder}, please make sure it exists.")
            else:
                # Get all supported image files
                for file in os.listdir(predesign_folder):
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        design_files.append(file)
            
            if not design_files:
                st.warning(f"No image files found in the {predesign_folder} folder.")
            else:
                # Display image selection interface
                selected_file = st.radio(
                    "Select a design:",
                    options=design_files,
                    horizontal=False
                )
                
                st.session_state.selected_preset = selected_file
                
                # Display selected design
                if st.session_state.selected_preset:
                    try:
                        # 加载选定的设计图像
                        design_path = os.path.join(predesign_folder, selected_file)
                        selected_design = Image.open(design_path).convert("RGBA")
                        st.image(selected_design, caption=f"Preset: {selected_file}", use_column_width=True)
                        
                        # 加载到临时设计变量，准备实时预览调整
                        st.session_state.temp_preset_design = selected_design
                        
                        # 调整位置和大小控件
                        st.markdown("### Adjust Position & Size")
                        
                        # 添加缩放滑块
                        scale_percent = st.slider("Size", 10, 100, st.session_state.temp_preset_scale, 5, 
                                                 help="Size of the design")
                        
                        # 设置水平和垂直位置的滑块
                        x_offset = st.slider("Horizontal", -100, 100, st.session_state.temp_preset_position[0], 5, 
                                           help="Move left/right")
                        y_offset = st.slider("Vertical", -100, 100, st.session_state.temp_preset_position[1], 5,
                                           help="Move up/down")
                        
                        # 当控制值改变时更新临时状态
                        if (x_offset, y_offset) != st.session_state.temp_preset_position or scale_percent != st.session_state.temp_preset_scale:
                            st.session_state.temp_preset_position = (x_offset, y_offset)
                            st.session_state.temp_preset_scale = scale_percent
                            st.rerun()  # 触发重新运行以更新预览
                        
                        # 应用设计按钮
                        if st.button("Apply to T-shirt", key="apply_preset"):
                            # 将临时设计和位置应用到实际设计
                            st.session_state.preset_design = st.session_state.temp_preset_design
                            st.session_state.preset_position = st.session_state.temp_preset_position
                            st.session_state.preset_scale = st.session_state.temp_preset_scale
                            
                            # 清除绘制的设计，确保只显示一种设计
                            st.session_state.drawn_design = None
                            
                            # 生成复合图像
                            update_composite_image()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error processing preset design: {e}")
        else:
            # 绘图设计界面
            st.markdown("## Draw Your Own Design")
            st.markdown("Create your own pattern:")
            
            pen_color = st.color_picker("Pen color", "#000000")
            pen_size = st.slider("Pen thickness", 1, 20, 5)
            
            # Drawing canvas
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 0.3)",  # Fill color
                stroke_width=pen_size,  # Stroke width
                stroke_color=pen_color,  # Stroke color
                background_color="#ffffff",  # Background color
                height=300,
                width=300,
                drawing_mode="freedraw",  # Drawing mode
                key="canvas",
            )

            # Check if there is a drawing
            if canvas_result.image_data is not None:
                # Button to apply to T-shirt
                if st.button("Apply Drawing to T-shirt", key="apply_drawing"):
                    # Convert numpy array to PIL image
                    drawn_design = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                    
                    # Create a new transparent background image
                    transparent_design = Image.new("RGBA", drawn_design.size, (0, 0, 0, 0))
                    
                    # Process image, making white background transparent
                    width, height = drawn_design.size
                    for x in range(width):
                        for y in range(height):
                            r, g, b, a = drawn_design.getpixel((x, y))
                            # If pixel is close to white, set it to fully transparent
                            if r > 240 and g > 240 and b > 240:
                                transparent_design.putpixel((x, y), (0, 0, 0, 0))
                            else:
                                # Otherwise keep original color and opacity
                                transparent_design.putpixel((x, y), (r, g, b, 255))
                    
                    # 存储绘制的设计到专用状态变量
                    st.session_state.drawn_design = transparent_design
                    
                    # 清除预设设计，确保只显示一种设计
                    st.session_state.preset_design = None
                    st.session_state.preset_position = (0, 0)
                    st.session_state.preset_scale = 40
                    
                    # 生成复合图像
                    update_composite_image()
                    st.rerun()
                
                if st.button("Clear Canvas", key="clear_canvas"):
                    # 不做任何操作，因为canvas会在页面刷新时自动清空
                    st.rerun()

    # 添加分隔线
    st.markdown("---")
    
    # Return to main interface button - 现在放在页面底部
    if st.button("Return to Main Page", key="return_to_main_page"):
        # Clear all design-related states
        st.session_state.base_image = None
        st.session_state.current_image = None
        st.session_state.current_box_position = None
        st.session_state.generated_design = None
        st.session_state.preset_design = None
        st.session_state.drawn_design = None
        st.session_state.final_design = None
        st.session_state.selected_preset = None
        st.session_state.temp_preset_design = None
        st.session_state.design_mode = "preset"  # 重置设计模式为默认值
        # Only change page state, retain user info and experiment group
        st.session_state.page = "welcome"
        st.rerun()

# 添加绘制预览的函数，直接在红框内展示设计
def draw_design_preview(image, design, box_position, design_position, design_scale):
    """在当前图像的红框内直接绘制设计预览"""
    # 创建图像副本
    img_copy = image.copy()
    
    # 获取红框位置和大小
    box_size = int(1024 * 0.25)
    left, top = box_position
    
    # 计算设计的位置和大小
    x_offset, y_offset = design_position
    scale_percent = design_scale
    
    # 计算缩放后的大小
    scaled_size = int(box_size * scale_percent / 100)
    
    # 计算可移动的范围
    max_offset = box_size - scaled_size
    # 将-100到100范围映射到实际的像素偏移
    actual_x_offset = int((x_offset / 100) * (max_offset / 2))
    actual_y_offset = int((y_offset / 100) * (max_offset / 2))
    
    # 计算预览的左上角坐标
    preview_left = left + (box_size - scaled_size) // 2 + actual_x_offset
    preview_top = top + (box_size - scaled_size) // 2 + actual_y_offset
    
    # 确保位置在红框范围内
    preview_left = max(left, min(preview_left, left + box_size - scaled_size))
    preview_top = max(top, min(preview_top, top + box_size - scaled_size))
    
    # 缩放设计图案
    design_scaled = design.resize((scaled_size, scaled_size), Image.LANCZOS)
    
    # 在预览位置粘贴设计图案（显示绿色边框）
    # 创建一个包含设计的新图像，并添加绿色边框
    preview_design = Image.new("RGBA", design_scaled.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(preview_design)
    
    # 创建一个新副本，避免直接修改原图
    design_with_border = design_scaled.copy()
    draw_border = ImageDraw.Draw(design_with_border)
    
    # 绘制绿色边框
    draw_border.rectangle(
        [(0, 0), (scaled_size-1, scaled_size-1)],
        outline=(0, 255, 0),  # 绿色
        width=2
    )
    
    try:
        # 粘贴带边框的设计到主图像
        img_copy.paste(design_with_border, (preview_left, preview_top), design_scaled)
    except Exception as e:
        st.warning(f"Transparent preview paste failed: {e}")
        img_copy.paste(design_with_border, (preview_left, preview_top))
    
    return img_copy

# 修改更新复合图像函数
def update_composite_image(preview_only=False):
    """更新复合图像，显示单种设计（只使用预设设计或绘制设计）"""
    # 创建基础图像的副本
    composite_image = st.session_state.base_image.copy()
    box_size = int(1024 * 0.25)
    left, top = st.session_state.current_box_position
    
    # 根据设计模式决定显示哪种设计
    if st.session_state.design_mode == "preset" and st.session_state.preset_design is not None:
        # 只显示预设设计
        # 获取位置偏移
        x_offset, y_offset = getattr(st.session_state, 'preset_position', (0, 0))
        scale_percent = getattr(st.session_state, 'preset_scale', 40)
        
        # 计算缩放大小 - 相对于选择框的百分比
        scaled_size = int(box_size * scale_percent / 100)
        
        # 根据偏移量计算具体位置
        # 计算可移动的范围，以确保图像不会完全移出框
        max_offset = box_size - scaled_size
        # 将-100到100范围映射到实际的像素偏移
        actual_x_offset = int((x_offset / 100) * (max_offset / 2))
        actual_y_offset = int((y_offset / 100) * (max_offset / 2))
        
        # 最终位置
        paste_x = left + (box_size - scaled_size) // 2 + actual_x_offset
        paste_y = top + (box_size - scaled_size) // 2 + actual_y_offset
        
        # 确保位置在合理范围内
        paste_x = max(left, min(paste_x, left + box_size - scaled_size))
        paste_y = max(top, min(paste_y, top + box_size - scaled_size))
        
        # 缩放预设图案
        preset_scaled = st.session_state.preset_design.resize((scaled_size, scaled_size), Image.LANCZOS)
        
        try:
            # 在计算的位置粘贴图像
            composite_image.paste(preset_scaled, (paste_x, paste_y), preset_scaled)
        except Exception as e:
            st.warning(f"Transparent channel paste failed for preset design: {e}")
            composite_image.paste(preset_scaled, (paste_x, paste_y))
    
    elif st.session_state.design_mode == "draw" and st.session_state.drawn_design is not None:
        # 只显示绘制的设计
        drawn_scaled = st.session_state.drawn_design.resize((box_size, box_size), Image.LANCZOS)
        try:
            composite_image.paste(drawn_scaled, (left, top), drawn_scaled)
        except Exception as e:
            st.warning(f"Transparent channel paste failed for drawn design: {e}")
            composite_image.paste(drawn_scaled, (left, top))
    
    # 如果不是仅预览，则保存最终设计
    if not preview_only:
        st.session_state.final_design = composite_image
    
    return composite_image

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
