import streamlit as st
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

# 需要先安装: pip install streamlit-image-coordinates
from streamlit_image_coordinates import streamlit_image_coordinates

# ========== Deepbricks 配置信息 ==========
from openai import OpenAI
API_KEY = "sk-lNVAREVHjj386FDCd9McOL7k66DZCUkTp6IbV0u9970qqdlg"
BASE_URL = "https://api.deepbricks.ai/v1/"
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
# ==============================================

# 设置页面配置
st.set_page_config(
    page_title="AI定制服装消费者行为实验平台",
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

# 初始化数据存储
DATA_FILE = "experiment_data.csv"

def initialize_experiment_data():
    """初始化或加载实验数据文件"""
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
    """保存实验数据到CSV文件"""
    try:
        df = pd.read_csv(DATA_FILE)
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"保存数据时出错: {e}")
        return False

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

def draw_selection_box(image, point=None):
    """在图像上绘制固定大小的选择框"""
    # 创建图像副本以避免修改原始图像
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    
    # 固定框的大小 (1024 * 0.25)
    box_size = int(1024 * 0.25)
    
    # 如果没有指定位置，则放在图片中心
    if point is None:
        x1 = (image.width - box_size) // 2
        y1 = (image.height - box_size) // 2
    else:
        x1, y1 = point
        # 确保选择框不会超出图片边界
        x1 = max(0, min(x1 - box_size//2, image.width - box_size))
        y1 = max(0, min(y1 - box_size//2, image.height - box_size))
    
    x2, y2 = x1 + box_size, y1 + box_size
    
    # 绘制红色轮廓
    draw.rectangle(
        [(x1, y1), (x2, y2)],
        outline=(255, 0, 0),
        width=2
    )
    
    # 创建单独的透明覆盖层用于填充
    overlay = Image.new('RGBA', img_copy.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    
    # 绘制半透明填充
    draw_overlay.rectangle(
        [(x1, y1), (x2, y2)],
        fill=(255, 0, 0, 50)
    )
    
    # 确保两个图像都是RGBA模式
    if img_copy.mode != 'RGBA':
        img_copy = img_copy.convert('RGBA')
    
    # 合成图像
    try:
        return Image.alpha_composite(img_copy, overlay), (x1, y1)
    except Exception as e:
        st.warning(f"图像合成失败: {e}")
        return img_copy, (x1, y1)

def get_selection_coordinates(point=None, image_size=None):
    """获取固定大小选择框的坐标和尺寸"""
    box_size = int(1024 * 0.25)
    
    if point is None and image_size is not None:
        width, height = image_size
        x1 = (width - box_size) // 2
        y1 = (height - box_size) // 2
    else:
        x1, y1 = point
        # 确保选择框不会超出图片边界
        if image_size:
            width, height = image_size
            x1 = max(0, min(x1 - box_size//2, width - box_size))
            y1 = max(0, min(y1 - box_size//2, height - box_size))
    
    return (x1, y1, box_size, box_size)

# 预设设计选项（用于非AI组）
PRESET_DESIGNS = {
    "花卉图案": "https://img.freepik.com/free-vector/hand-drawn-floral-design_23-2148852577.jpg",
    "几何图案": "https://img.freepik.com/free-vector/geometric-pattern-background_23-2148629793.jpg",
    "抽象艺术": "https://img.freepik.com/free-vector/abstract-design-background_23-2148772796.jpg",
    "简约线条": "https://img.freepik.com/free-vector/minimalist-background-with-line-design_23-2148822200.jpg",
    "动物图案": "https://img.freepik.com/free-vector/hand-drawn-animal-pattern_23-2148703902.jpg"
}

# 初始化会话状态
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

# 确保数据文件存在
initialize_experiment_data()

# 欢迎与信息收集页面
def show_welcome_page():
    st.title("👕 AI定制服装消费者行为实验平台")
    
    with st.container():
        st.markdown('<div class="welcome-card">', unsafe_allow_html=True)
        st.markdown("### 欢迎参与我们的实验！")
        st.markdown("""
        本实验旨在研究不同服装定制方式对消费者购买行为的影响。您将有机会体验T恤定制过程，并分享您的反馈。
        
        **实验流程**：
        1. 填写基本信息
        2. 选择实验组别
        3. 完成T恤定制
        4. 提交问卷反馈
        
        您的参与对我们的研究至关重要，非常感谢您的支持！
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### 请填写您的基本信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        age = st.number_input("您的年龄", min_value=18, max_value=80, value=25)
        
        gender = st.radio("您的性别", 
                          options=["男", "女", "其他", "不愿透露"])
    
    with col2:
        shopping_frequency = st.selectbox(
            "您购买服装的频率是？",
            options=["每周都购买", "每月购买几次", "每季度购买", "每年购买几次", "极少购买"]
        )
        
        customize_experience = st.selectbox(
            "您之前是否有过服装定制经验？",
            options=["有很多经验", "有一些经验", "很少有经验", "从未尝试过"]
        )
    
    ai_attitude = st.slider(
        "您对人工智能技术的态度如何？",
        min_value=1, max_value=10, value=5,
        help="1表示非常消极，10表示非常积极"
    )
    
    uniqueness_importance = st.slider(
        "服装独特性对您的重要程度如何？",
        min_value=1, max_value=10, value=5,
        help="1表示完全不重要，10表示非常重要"
    )
    
    st.markdown("### 请选择您要参与的实验组别")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="group-card">', unsafe_allow_html=True)
        st.markdown("#### AI定制组")
        st.markdown("""
        - 使用人工智能技术生成定制图案
        - 根据您的喜好和描述创建独特设计
        - 在T恤上自由放置设计图案
        """)
        if st.button("选择AI定制组"):
            st.session_state.experiment_group = "AI定制组"
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
        st.markdown("#### 预设设计组")
        st.markdown("""
        - 从精选的设计库中选择图案
        - 高质量专业设计
        - 在T恤上自由放置选定的图案
        """)
        if st.button("选择预设设计组"):
            st.session_state.experiment_group = "预设设计组"
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

    # 管理员区域 - 实验数据分析（通过密码保护）
    st.markdown("---")
    with st.expander("实验数据分析（仅管理员）"):
        admin_password = st.text_input("管理员密码", type="password")
        if admin_password == "admin123":  # 简单密码示例，实际应用中应使用更安全的认证方式
            try:
                # 读取实验数据
                experiment_df = pd.read_csv(DATA_FILE)
                
                if not experiment_df.empty:
                    st.markdown("### 实验数据统计")
                    
                    # 基本统计信息
                    st.markdown("#### 参与人数统计")
                    group_counts = experiment_df['experiment_group'].value_counts()
                    st.write(f"总参与人数: {len(experiment_df)}")
                    st.write(f"AI定制组: {group_counts.get('AI定制组', 0)}人")
                    st.write(f"预设设计组: {group_counts.get('预设设计组', 0)}人")
                    
                    # 购买意向对比
                    st.markdown("#### 购买意向对比")
                    purchase_by_group = experiment_df.groupby('experiment_group')['purchase_intent'].mean()
                    st.bar_chart(purchase_by_group)
                    
                    # 满意度对比
                    st.markdown("#### 满意度对比")
                    satisfaction_by_group = experiment_df.groupby('experiment_group')['satisfaction_score'].mean()
                    st.bar_chart(satisfaction_by_group)
                    
                    # 愿意支付价格对比
                    st.markdown("#### 愿意支付价格对比")
                    price_by_group = experiment_df.groupby('experiment_group')['price_willing_to_pay'].mean()
                    st.bar_chart(price_by_group)
                    
                    # 导出数据按钮
                    st.download_button(
                        label="导出完整数据 (CSV)",
                        data=experiment_df.to_csv(index=False).encode('utf-8'),
                        file_name="experiment_data_export.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("暂无实验数据，请等待用户参与实验。")
            except Exception as e:
                st.error(f"加载或分析数据时出错: {e}")
        elif admin_password:
            st.error("密码错误，无法访问管理员区域。")

# AI定制组设计页面
def show_ai_design_page():
    st.title("👕 AI定制服装实验平台")
    st.markdown("### AI定制组 - 创建您独特的T恤设计")
    
    # 创建两列布局
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("## 设计区域")
        
        # 加载衬衫底图
        if st.session_state.base_image is None:
            try:
                base_image = Image.open("white_shirt.png").convert("RGBA")
                st.session_state.base_image = base_image
                # 初始化时在中心绘制选择框
                initial_image, initial_pos = draw_selection_box(base_image)
                st.session_state.current_image = initial_image
                st.session_state.current_box_position = initial_pos
            except Exception as e:
                st.error(f"加载白衬衫图片时出错: {e}")
                st.stop()
        
        st.markdown("**👇 点击T恤上的任意位置来移动设计框**")
        
        # 显示当前图像并获取点击坐标
        current_image = st.session_state.current_image
        coordinates = streamlit_image_coordinates(
            current_image,
            key="shirt_image"
        )
        
        # 处理选择区域逻辑 - 简化为直接移动红框
        if coordinates:
            # 更新当前鼠标位置的选择框
            current_point = (coordinates["x"], coordinates["y"])
            temp_image, new_pos = draw_selection_box(st.session_state.base_image, current_point)
            st.session_state.current_image = temp_image
            st.session_state.current_box_position = new_pos
            st.rerun()

    with col2:
        st.markdown("## 设计参数")
        
        # 用户输入个性化参数
        theme = st.text_input("主题或关键词 (必填)", "花卉图案")
        style = st.text_input("设计风格", "abstract")
        colors = st.text_input("偏好颜色", "pink, gold")
        details = st.text_area("更多细节", "some swirling shapes")
        
        # 生成设计按钮
        if st.button("🎨 生成AI设计"):
            if not theme.strip():
                st.warning("请至少输入主题或关键词！")
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
                        
                        # 将设计图放置到当前选择位置
                        left, top = st.session_state.current_box_position
                        box_size = int(1024 * 0.25)
                        
                        # 将生成图案缩放到选择区域大小
                        scaled_design = custom_design.resize((box_size, box_size), Image.LANCZOS)
                        
                        try:
                            # 确保使用透明通道进行粘贴
                            composite_image.paste(scaled_design, (left, top), scaled_design)
                        except Exception as e:
                            st.warning(f"使用透明通道粘贴失败，直接粘贴: {e}")
                            composite_image.paste(scaled_design, (left, top))
                        
                        st.session_state.final_design = composite_image
                        st.rerun()
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
        
        # 返回主界面按钮
        if st.button("返回主界面"):
            st.session_state.page = "welcome"
            st.rerun()

# 预设设计组设计页面
def show_preset_design_page():
    st.title("👕 预设设计服装实验平台")
    st.markdown("### 预设设计组 - 选择您喜欢的T恤设计")
    
    # 创建两列布局
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("## 设计区域")
        
        # 加载衬衫底图
        if st.session_state.base_image is None:
            try:
                base_image = Image.open("white_shirt.png").convert("RGBA")
                st.session_state.base_image = base_image
                # 初始化时在中心绘制选择框
                initial_image, initial_pos = draw_selection_box(base_image)
                st.session_state.current_image = initial_image
                st.session_state.current_box_position = initial_pos
            except Exception as e:
                st.error(f"加载白衬衫图片时出错: {e}")
                st.stop()
        
        st.markdown("**👇 点击T恤上的任意位置来移动设计框**")
        
        # 显示当前图像并获取点击坐标
        current_image = st.session_state.current_image
        coordinates = streamlit_image_coordinates(
            current_image,
            key="shirt_image"
        )
        
        # 处理选择区域逻辑 - 简化为直接移动红框
        if coordinates:
            # 更新当前鼠标位置的选择框
            current_point = (coordinates["x"], coordinates["y"])
            temp_image, new_pos = draw_selection_box(st.session_state.base_image, current_point)
            st.session_state.current_image = temp_image
            st.session_state.current_box_position = new_pos
            st.rerun()

    with col2:
        st.markdown("## 选择预设设计")
        
        # 显示预设设计选项
        st.markdown("从以下设计中选择一个：")
        
        # 创建网格展示预设设计
        st.markdown('<div class="design-gallery">', unsafe_allow_html=True)
        
        # 显示预设设计图片供选择
        selected_design = st.radio(
            "设计选项",
            options=list(PRESET_DESIGNS.keys()),
            horizontal=True
        )
        
        st.session_state.selected_preset = selected_design
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 显示选中的设计
        if st.session_state.selected_preset:
            st.markdown(f"### 已选择: {st.session_state.selected_preset}")
            
            # 获取预设设计图片
            design_url = PRESET_DESIGNS[st.session_state.selected_preset]
            
            try:
                # 下载预设设计图片
                response = requests.get(design_url)
                if response.status_code == 200:
                    preset_design = Image.open(BytesIO(response.content)).convert("RGBA")
                    st.image(preset_design, caption="预设设计", use_column_width=True)
                    
                    # 应用设计按钮
                    if st.button("应用到T恤上"):
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
                            st.warning(f"使用透明通道粘贴失败，直接粘贴: {e}")
                            composite_image.paste(scaled_design, (left, top))
                        
                        st.session_state.final_design = composite_image
                        st.rerun()
                else:
                    st.error(f"无法加载预设设计图片，错误码：{response.status_code}")
            except Exception as e:
                st.error(f"处理预设设计时出错: {e}")
        
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
        
        # 返回主界面按钮
        if st.button("返回主界面"):
            st.session_state.page = "welcome"
            st.rerun()

# 问卷页面
def show_survey_page():
    st.title("👕 服装定制实验问卷")
    st.markdown(f"### {st.session_state.experiment_group} - 您的反馈")
    
    if not st.session_state.submitted:
        st.markdown('<div class="purchase-intent">', unsafe_allow_html=True)
        
        # 计算设计花费的时间
        design_duration = (datetime.datetime.now() - st.session_state.start_time).total_seconds() / 60
        
        # 购买意向
        purchase_intent = st.slider(
            "如果这件T恤在市场上销售，您购买此产品的可能性有多大？",
            min_value=1, max_value=10, value=5,
            help="1表示绝对不会购买，10表示一定会购买"
        )
        
        # 满意度评分
        satisfaction_score = st.slider(
            "您对最终设计效果的满意度？",
            min_value=1, max_value=10, value=5,
            help="1表示非常不满意，10表示非常满意"
        )
        
        # 不同组别的特有问题
        if st.session_state.experiment_group == "AI定制组":
            # AI定制组特有问题
            ai_effectiveness = st.slider(
                "您认为AI生成的设计有多符合您的期望？",
                min_value=1, max_value=10, value=5,
                help="1表示完全不符合期望，10表示完全符合期望"
            )
            
            ai_uniqueness = st.slider(
                "您认为AI生成的设计有多独特？",
                min_value=1, max_value=10, value=5,
                help="1表示一点都不独特，10表示非常独特"
            )
            
            ai_experience = st.radio(
                "使用AI定制服装的体验与您之前的购物体验相比如何？",
                options=["更好", "差不多", "更差", "无法比较"]
            )
            
            ai_future = st.radio(
                "未来您是否会考虑使用AI定制服装？",
                options=["一定会", "可能会", "可能不会", "一定不会"]
            )
        else:
            # 预设设计组特有问题
            design_variety = st.slider(
                "您对预设设计种类的满意度如何？",
                min_value=1, max_value=10, value=5,
                help="1表示非常不满意，10表示非常满意"
            )
            
            design_quality = st.slider(
                "您对所选设计质量的评价如何？",
                min_value=1, max_value=10, value=5,
                help="1表示质量很差，10表示质量极佳"
            )
            
            design_preference = st.radio(
                "您更偏好哪种类型的服装设计？",
                options=["大众流行款式", "少见的独特设计", "个性化定制设计", "简约基础款式"]
            )
            
            design_limitation = st.radio(
                "您是否感到预设设计限制了您的创意表达？",
                options=["非常限制", "有些限制", "几乎没有限制", "完全不限制"]
            )
        
        # 两组共同问题
        customize_difficulty = st.slider(
            "您认为使用本系统定制T恤的难度如何？",
            min_value=1, max_value=10, value=5,
            help="1表示非常困难，10表示非常容易"
        )
        
        # 购买意愿价格
        price_willing_to_pay = st.slider(
            "您愿意为这件定制T恤支付多少元人民币？",
            min_value=0, max_value=500, value=100, step=10
        )
        
        # 开放式反馈
        feedback = st.text_area(
            "请分享您对此定制体验的任何其他反馈或建议",
            height=100
        )
        
        # 提交按钮
        if st.button("提交反馈"):
            # 收集所有数据
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
                'theme': st.session_state.selected_preset if st.session_state.experiment_group == "预设设计组" else None,
                'design_choice': st.session_state.selected_preset if st.session_state.experiment_group == "预设设计组" else None,
                'uniqueness_importance': st.session_state.user_info.get('uniqueness_importance'),
                'ai_attitude': st.session_state.user_info.get('ai_attitude'),
                'feedback': feedback
            }
            
            # 添加不同组别的特有数据
            if st.session_state.experiment_group == "AI定制组":
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
            
            # 保存数据
            if save_experiment_data(experiment_data):
                st.session_state.submitted = True
                st.success("感谢您的反馈！您的数据已被记录，将有助于我们的研究。")
                st.rerun()
            else:
                st.error("保存反馈数据失败，请重试。")
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.success("您已成功提交问卷！感谢您的参与。")
        
        if st.button("返回主界面"):
            # 重置会话状态
            for key in list(st.session_state.keys()):
                if key != 'user_id':  # 保留用户ID以便跟踪
                    del st.session_state[key]
            st.session_state.page = "welcome"
            st.rerun()

# 主程序控制逻辑
def main():
    # 初始化数据文件
    initialize_experiment_data()
    
    # 根据当前页面显示不同内容
    if st.session_state.page == "welcome":
        show_welcome_page()
    elif st.session_state.page == "design":
        if st.session_state.experiment_group == "AI定制组":
            show_ai_design_page()
        elif st.session_state.experiment_group == "预设设计组":
            show_preset_design_page()
        else:
            st.error("实验组类型错误，请返回首页重新选择")
            if st.button("返回首页"):
                st.session_state.page = "welcome"
                st.rerun()
    elif st.session_state.page == "survey":
        show_survey_page()

# 运行应用
if __name__ == "__main__":
    main()
