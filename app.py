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

# Required: pip install streamlit-image-coordinates
from streamlit_image_coordinates import streamlit_image_coordinates

# ========== Deepbricks Configuration ==========
from openai import OpenAI
API_KEY = "sk-lNVAREVHjj386FDCd9McOL7k66DZCUkTp6IbV0u9970qqdlg"
BASE_URL = "https://api.deepbricks.ai/v1/"
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
# ==============================================

# Set page configuration
st.set_page_config(
    page_title="AI Customized Clothing Consumer Behavior Experiment Platform",
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
    """Initialize or load the experiment data file"""
    if not os.path.exists(DATA_FILE):
        try:
            df = pd.DataFrame(columns=[
                'user_id', 'experiment_group', 'timestamp', 'design_duration', 
                'age', 'gender', 'shopping_frequency', 'purchase_intent', 
                'satisfaction_score', 'customize_difficulty',
                'price_willing_to_pay', 'theme', 'design_choice', 'uniqueness_importance',
                'ai_attitude', 'feedback'
            ])
            df.to_csv(DATA_FILE, index=False)
            return True
        except Exception as e:
            st.error(f"Error creating data file: {e}")
            return False
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
    """Generate an image based on the prompt using the API"""
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

    if resp and hasattr(resp, 'data') and len(resp.data) > 0 and hasattr(resp.data[0], 'url') and resp.data[0].url:
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
        st.error("Failed to get image URL from API response.")
    return None

def draw_selection_box(image, point=None):
    """Draw a fixed-size selection box on the image"""
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    
    box_size = int(1024 * 0.25)
    
    if point is None:
        x1 = (image.width - box_size) // 2
        y1 = (image.height - box_size) // 2
    else:
        x1, y1 = point
        x1 = max(0, min(x1 - box_size//2, image.width - box_size))
        y1 = max(0, min(y1 - box_size//2, image.height - box_size))
    
    x2, y2 = x1 + box_size, y1 + box_size
    
    draw.rectangle(
        [(x1, y1), (x2, y2)],
        outline=(255, 0, 0),
        width=2
    )
    
    overlay = Image.new('RGBA', img_copy.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    
    draw_overlay.rectangle(
        [(x1, y1), (x2, y2)],
        fill=(255, 0, 0, 50)
    )
    
    if img_copy.mode != 'RGBA':
        img_copy = img_copy.convert('RGBA')
    
    try:
        return Image.alpha_composite(img_copy, overlay), (x1, y1)
    except Exception as e:
        st.warning(f"Image composition failed: {e}")
        return img_copy, (x1, y1)

def get_selection_coordinates(point=None, image_size=None):
    """Get coordinates and size of the fixed-size selection box"""
    box_size = int(1024 * 0.25)
    
    if point is None and image_size is not None:
        width, height = image_size
        x1 = (width - box_size) // 2
        y1 = (height - box_size) // 2
    else:
        x1, y1 = point
        if image_size:
            width, height = image_size
            x1 = max(0, min(x1 - box_size//2, width - box_size))
            y1 = max(0, min(y1 - box_size//2, height - box_size))
    
    return (x1, y1, box_size, box_size)

def match_background_to_shirt(design_image, shirt_image):
    """Adjust the background color of the design pattern to match the shirt"""
    design_image = design_image.convert("RGBA")
    shirt_image = shirt_image.convert("RGBA")
    
    shirt_bg_color = shirt_image.getpixel((0, 0))
    
    datas = design_image.getdata()
    newData = []
    
    for item in datas:
        if item[3] == 0:
            newData.append(item)
        else:
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
    st.title("👕 AI Customized Clothing Consumer Behavior Experiment Platform")
    
    with st.container():
        st.markdown('<div class="welcome-card">', unsafe_allow_html=True)
        st.markdown("### Welcome to our experiment!")
        st.markdown("""
        This experiment aims to study the impact of different clothing customization methods on consumer purchasing behavior. You will have the opportunity to experience the T-shirt customization process and share your feedback.
        
        **Experiment Process**:
        1. Fill in basic information
        2. Choose an experimental group
        3. Complete T-shirt customization
        4. Submit questionnaire feedback
        
        Your participation is crucial to our research, thank you for your support!
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### Please fill in your basic information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        age = st.number_input("Your Age", min_value=18, max_value=80, value=25)
        
        gender = st.radio("Your Gender", 
                          options=["Male", "Female", "Other", "Prefer not to say"])
    
    with col2:
        shopping_frequency = st.selectbox(
            "How often do you buy clothing?",
            options=["Every week", "A few times a month", "Once a quarter", "A few times a year", "Rarely"]
        )
        
        customize_experience = st.selectbox(
            "Do you have any experience with clothing customization?",
            options=["A lot of experience", "Some experience", "Very little experience", "Never tried"]
        )
    
    ai_attitude = st.slider(
        "How do you feel about AI technology?",
        min_value=1, max_value=10, value=5,
        help="1 means very negative, 10 means very positive"
    )
    
    uniqueness_importance = st.slider(
        "How important is clothing uniqueness to you?",
        min_value=1, max_value=10, value=5,
        help="1 means not important at all, 10 means very important"
    )
    
    st.markdown("### Please choose the experimental group you want to participate in")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="group-card">', unsafe_allow_html=True)
        st.markdown("#### AI Customization Group")
        st.markdown("""
        - Use AI technology to generate custom patterns
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

    # Admin area - Experiment data analysis (password protected)
    st.markdown("---")
    with st.expander("Experiment Data Analysis (Admin Only)"):
        admin_password = st.text_input("Admin Password", type="password")
        if admin_password == "admin123":  # Simple password example, should use a more secure authentication method in practice
            try:
                # Read experiment data
                experiment_df = pd.read_csv(DATA_FILE)
                
                if not experiment_df.empty:
                    st.markdown("### Experiment Data Statistics")
                    
                    # Basic statistics
                    st.markdown("#### Participant Count")
                    group_counts = experiment_df['experiment_group'].value_counts()
                    st.write(f"Total Participants: {len(experiment_df)}")
                    st.write(f"AI Customization Group: {group_counts.get('AI Customization Group', 0)} people")
                    st.write(f"Preset Design Group: {group_counts.get('Preset Design Group', 0)} people")
                    
                    # Purchase intent comparison
                    st.markdown("#### Purchase Intent Comparison")
                    purchase_by_group = experiment_df.groupby('experiment_group')['purchase_intent'].mean()
                    st.bar_chart(purchase_by_group)
                    
                    # Satisfaction comparison
                    st.markdown("#### Satisfaction Comparison")
                    satisfaction_by_group = experiment_df.groupby('experiment_group')['satisfaction_score'].mean()
                    st.bar_chart(satisfaction_by_group)
                    
                    # Willingness to pay comparison
                    st.markdown("#### Willingness to Pay Comparison")
                    price_by_group = experiment_df.groupby('experiment_group')['price_willing_to_pay'].mean()
                    st.bar_chart(price_by_group)
                    
                    # Export data button
                    st.download_button(
                        label="Export Full Data (CSV)",
                        data=experiment_df.to_csv(index=False).encode('utf-8'),
                        file_name="experiment_data_export.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No experiment data available, please wait for user participation.")
            except Exception as e:
                st.error(f"Error loading or analyzing data: {e}")
        elif admin_password:
            st.error("Incorrect password, unable to access admin area.")

# AI Customization Group Design Page
def show_ai_design_page():
    st.title("👕 AI Customized Clothing Experiment Platform")
    st.markdown("### AI Customization Group - Create Your Unique T-shirt Design")
    
    # Create two-column layout
col1, col2 = st.columns([3, 2])

with col1:
        st.markdown("## Design Area")
    
        # Load shirt base image
    if st.session_state.base_image is None:
        try:
            base_image = Image.open("white_shirt.png").convert("RGBA")
            st.session_state.base_image = base_image
            initial_image, initial_pos = draw_selection_box(base_image)
            st.session_state.current_image = initial_image
            st.session_state.current_box_position = initial_pos
        except Exception as e:
                st.error(f"Error loading white shirt image: {e}")
            st.stop()
    
        st.markdown("**👇 Click anywhere on the T-shirt to move the design box**")
        
        # Display current image and get click coordinates
    current_image = st.session_state.current_image
    coordinates = streamlit_image_coordinates(
        current_image,
        key="shirt_image"
    )
    
        # Handle selection area logic - simplified to directly move the red box
        if coordinates:
        current_point = (coordinates["x"], coordinates["y"])
        temp_image, new_pos = draw_selection_box(st.session_state.base_image, current_point)
        st.session_state.current_image = temp_image
        st.session_state.current_box_position = new_pos
            st.rerun()
    
    with col2:
        st.markdown("## Design Parameters")
        
        # User input for personalization parameters
        theme = st.text_input("Theme or Keywords (Required)", "Floral Pattern")
        style = st.text_input("Design Style", "abstract")
        colors = st.text_input("Preferred Colors", "pink, gold")
        details = st.text_area("More Details", "some swirling shapes")
        
        # Generate design button
        if st.button("🎨 Generate AI Design"):
        if not theme.strip():
                st.warning("Please enter at least a theme or keywords!")
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
                    
                        # Composite on the base image
                    composite_image = st.session_state.base_image.copy()
                    
                        left, top = st.session_state.current_box_position
                        box_size = int(1024 * 0.25)
                        
                        scaled_design = custom_design.resize((box_size, box_size), Image.LANCZOS)
                        
                        try:
                            composite_image.paste(scaled_design, (left, top), scaled_design)
                        except Exception as e:
                            st.warning(f"Failed to paste using transparency channel, pasting directly: {e}")
                            composite_image.paste(scaled_design, (left, top))
                        
                        st.session_state.final_design = composite_image
                        st.rerun()
                    else:
                        st.error("Failed to generate image, please try again later.")
    
    # Display final effect - moved to the bottom of the overall page
    if st.session_state.final_design is not None:
        st.markdown("### Final Effect")
        st.image(st.session_state.final_design, use_container_width=True)  # Use new parameter
        
        # Provide download option
        col1, col2 = st.columns(2)
        with col1:
            buf = BytesIO()
            st.session_state.final_design.save(buf, format="PNG")
            buf.seek(0)
            st.download_button(
                label="💾 Download Custom Effect",
                data=buf,
                file_name="custom_tshirt.png",
                mime="image/png"
            )
        
        with col2:
            # Confirm completion button
            if st.button("Confirm Completion"):
                st.session_state.page = "survey"
                st.rerun()
    
    # Return to main interface button - single line, consistent with AI customization page
    if st.button("Return to Main Interface"):
        # Clear all design-related states
        st.session_state.base_image = None
        st.session_state.current_image = None
        st.session_state.current_box_position = None
        st.session_state.generated_design = None
        st.session_state.final_design = None
        st.session_state.selected_preset = None  # Clear selected preset design
        st.session_state.page = "welcome"
        st.rerun()

# Preset Design Group Design Page
def show_preset_design_page():
    st.title("👕 Preset Design Clothing Experiment Platform")
    st.markdown("### Preset Design Group - Choose Your Favorite T-shirt Design")
    
    # Create two-column layout
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("## Design Area")
        
        # Load shirt base image
        if st.session_state.base_image is None:
            try:
                base_image = Image.open("white_shirt.png").convert("RGBA")
                st.session_state.base_image = base_image
                initial_image, initial_pos = draw_selection_box(base_image)
                st.session_state.current_image = initial_image
                st.session_state.current_box_position = initial_pos
            except Exception as e:
                st.error(f"Error loading white shirt image: {e}")
                st.stop()
        
        st.markdown("**👇 Click anywhere on the T-shirt to move the design box**")
        
        # Display current image and get click coordinates
        current_image = st.session_state.current_image
        coordinates = streamlit_image_coordinates(
            current_image,
            key="shirt_image"
        )
        
        # Handle selection area logic - simplified to directly move the red box
        if coordinates:
            current_point = (coordinates["x"], coordinates["y"])
            temp_image, new_pos = draw_selection_box(st.session_state.base_image, current_point)
            st.session_state.current_image = temp_image
            st.session_state.current_box_position = new_pos
            st.rerun()

    with col2:
        st.markdown("## Choose Preset Design")
        
        # Display preset design image options
        st.markdown("Choose one from the following designs:")
        
        predesign_folder = "predesign"
        design_files = []
        
        # 确保文件夹存在或创建默认文件夹
        if not os.path.exists(predesign_folder):
            try:
                os.makedirs(predesign_folder)
                st.warning(f"Created preset design folder: {predesign_folder}. Please add design files to this folder.")
            except Exception as e:
                st.error(f"Cannot create preset design folder: {predesign_folder}. Error: {e}")
        
        # 更健壮的文件处理
        if os.path.exists(predesign_folder):
            for file in os.listdir(predesign_folder):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    design_files.append(file)
            
            if not design_files:
                st.warning(f"No image files found in {predesign_folder}. Please add design files to this folder.")
            else:
                selected_file = st.radio(
                    "Available Designs",
                    options=design_files,
                    horizontal=True
                )
                
                st.session_state.selected_preset = selected_file
                
                if st.session_state.selected_preset:
                    try:
                        design_path = os.path.join(predesign_folder, selected_file)
                        if not os.path.exists(design_path):
                            st.error(f"Selected design file {design_path} not found.")
                        else:
                            preset_design = Image.open(design_path).convert("RGBA")
                            st.image(preset_design, caption=f"Preset Design: {selected_file}", use_container_width=True)
                            
                            # 应用设计按钮
                            if st.button("Apply to T-shirt"):
                                st.session_state.generated_design = preset_design
                                
                                # 在原图上合成
                                composite_image = st.session_state.base_image.copy()
                                
                                # 将设计图放置到当前选择位置
                                left, top = st.session_state.current_box_position
                                box_size = int(1024 * 0.25)
                                
                                # 将预设图案缩放到选择区域大小
                                scaled_design = preset_design.resize((box_size, box_size), Image.LANCZOS)
                            
                            try:
                                # 确保使用透明通道进行粘贴
                                composite_image.paste(scaled_design, (left, top), scaled_design)
                            except Exception as e:
                                    st.warning(f"Failed to paste using transparency channel, pasting directly: {e}")
                                composite_image.paste(scaled_design, (left, top))
                    
                    st.session_state.final_design = composite_image
                    st.rerun()
                    except Exception as e:
                        st.error(f"Error processing preset design: {e}")

    # Display final effect - consistent layout with AI customization page
    if st.session_state.final_design is not None:
        st.markdown("### Final Effect")
        st.image(st.session_state.final_design, use_container_width=True)  # Use new parameter
        
        col1, col2 = st.columns(2)
        with col1:
        buf = BytesIO()
        st.session_state.final_design.save(buf, format="PNG")
        buf.seek(0)
        st.download_button(
                label="💾 Download Custom Effect",
            data=buf,
            file_name="custom_tshirt.png",
            mime="image/png"
        )

        with col2:
            if st.button("Confirm Completion"):
                st.session_state.page = "survey"
                st.rerun()

    # Return to main interface button - single line, consistent with AI customization page
    if st.button("Return to Main Interface"):
        # Clear all design-related states
        st.session_state.base_image = None
        st.session_state.current_image = None
        st.session_state.current_box_position = None
        st.session_state.generated_design = None
        st.session_state.final_design = None
        st.session_state.selected_preset = None  # Clear selected preset design
        st.session_state.page = "welcome"
        st.rerun()

# Survey Page
def show_survey_page():
    st.title("👕 Clothing Customization Experiment Questionnaire")
    st.markdown(f"### {st.session_state.experiment_group} - Your Feedback")
    
    if not st.session_state.submitted:
        st.markdown('<div class="purchase-intent">', unsafe_allow_html=True)
        
        # 确保start_time存在
        if 'start_time' not in st.session_state:
            st.session_state.start_time = datetime.datetime.now()
        
        design_duration = (datetime.datetime.now() - st.session_state.start_time).total_seconds() / 60
        
        purchase_intent = st.slider(
            "If this T-shirt were sold on the market, how likely are you to purchase this product?",
            min_value=1, max_value=10, value=5,
            help="1 means definitely won't buy, 10 means definitely will buy"
        )
        
        satisfaction_score = st.slider(
            "How satisfied are you with the final design?",
            min_value=1, max_value=10, value=5,
            help="1 means very dissatisfied, 10 means very satisfied"
        )
        
        if st.session_state.experiment_group == "AI Customization Group":
            ai_effectiveness = st.slider(
                "How well do you think the AI-generated design meets your expectations?",
                min_value=1, max_value=10, value=5,
                help="1 means does not meet expectations at all, 10 means fully meets expectations"
            )
            
            ai_uniqueness = st.slider(
                "How unique do you think the AI-generated design is?",
                min_value=1, max_value=10, value=5,
                help="1 means not unique at all, 10 means very unique"
            )
            
            ai_experience = st.radio(
                "How does the experience of using AI customization compare to your previous shopping experiences?",
                options=["Better", "About the same", "Worse", "Cannot compare"]
            )
            
            ai_future = st.radio(
                "In the future, would you consider using AI for clothing customization?",
                options=["Definitely will", "Probably will", "Probably won't", "Definitely won't"]
            )
        else:
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
                "What type of clothing design do you prefer?",
                options=["Popular styles", "Rare unique designs", "Personalized custom designs", "Simple basic styles"]
            )
            
            design_limitation = st.radio(
                "Do you feel that preset designs limit your creative expression?",
                options=["Very limiting", "Somewhat limiting", "Barely limiting", "Not limiting at all"]
            )
        
        customize_difficulty = st.slider(
            "How difficult do you think it is to customize a T-shirt using this system?",
            min_value=1, max_value=10, value=5,
            help="1 means very difficult, 10 means very easy"
        )
        
        price_willing_to_pay = st.slider(
            "How much are you willing to pay for this customized T-shirt (in RMB)?",
            min_value=0, max_value=500, value=100, step=10
        )
        
        feedback = st.text_area(
            "Please share any additional feedback or suggestions regarding this customization experience",
            height=100
        )
        
        if st.button("Submit Feedback"):
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
            
            if st.session_state.experiment_group == "AI Customization Group":
                experiment_data.update({
                    'ai_effectiveness': ai_effectiveness,
                    'ai_uniqueness': ai_uniqueness,
                    'ai_experience': ai_experience,
                    'ai_future': ai_future,
                    'design_variety': None,
                    'design_quality': None,
                    'design_preference': None,
                    'design_limitation': None
                })
            else:
                experiment_data.update({
                    'design_variety': design_variety,
                    'design_quality': design_quality,
                    'design_preference': design_preference,
                    'design_limitation': design_limitation,
                    'ai_effectiveness': None,
                    'ai_uniqueness': None,
                    'ai_experience': None,
                    'ai_future': None
                })
            
            if save_experiment_data(experiment_data):
                st.session_state.submitted = True
                st.success("Thank you for your feedback! Your data has been recorded and will help our research.")
                st.rerun()
            else:
                st.error("Failed to save feedback data, please try again.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.success("You have successfully submitted the questionnaire! Thank you for your participation.")
        
        if st.button("Return to Main Interface"):
            # Reset session state
            for key in list(st.session_state.keys()):
                if key != 'user_id':  # Keep user ID for tracking
                    del st.session_state[key]
            st.session_state.page = "welcome"
            st.rerun()

# Main program control logic
def main():
    # Initialize data file
    initialize_experiment_data()
    
    # Display different content based on the current page
    if st.session_state.page == "welcome":
        show_welcome_page()
    elif st.session_state.page == "design":
        if st.session_state.experiment_group == "AI Customization Group":
            show_ai_design_page()
        elif st.session_state.experiment_group == "Preset Design Group":
            show_preset_design_page()
        else:
            st.error("Experiment group type error, please return to the homepage to reselect.")
            if st.button("Return to Homepage"):
                st.session_state.page = "welcome"
                st.rerun()
    elif st.session_state.page == "survey":
        show_survey_page()

# Run the application
if __name__ == "__main__":
    main()
