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
import random

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
</style>
""", unsafe_allow_html=True)

# 初始化数据存储
DATA_FILE = "experiment_data.csv"

def initialize_experiment_data():
    """初始化或加载实验数据文件"""
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            'user_id', 'experiment_group', 'timestamp', 'design_duration', 
            'purchase_intent', 'satisfaction_score', 'customize_difficulty',
            'price_willing_to_pay', 'theme', 'style', 'colors', 'details',
            'feedback'
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

# 预设设计选项（用于对照组）
PRESET_DESIGNS = {
    "花卉图案": "preset_floral.png",
    "几何图案": "preset_geometric.png",
    "抽象艺术": "preset_abstract.png",
    "简约线条": "preset_minimal.png",
    "动物图案": "preset_animal.png"
}

# 初始化会话状态
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if 'experiment_group' not in st.session_state:
    # 随机分配实验组：AI定制组(True)或预设设计组(False)
    st.session_state.experiment_group = random.choice([True, False])
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()
if 'selection_mode' not in st.session_state:
    st.session_state.selection_mode = False
if 'selection_areas' not in st.session_state:
    st.session_state.selection_areas = []
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

# 确保数据文件存在
initialize_experiment_data()

# 实验分组说明
group_name = "AI定制组" if st.session_state.experiment_group else "预设设计组"

# 标题
st.title("👕 AI定制服装消费者行为实验平台")
st.markdown(f"### 您当前在：{group_name}")

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
    
    # 选择模式按钮
    if st.button("🖱️ " + ("退出选择模式" if st.session_state.selection_mode else "进入选择模式")):
        st.session_state.selection_mode = not st.session_state.selection_mode
        if not st.session_state.selection_mode:
            # 退出选择模式时，如果没有确认的选区，则恢复到中心位置
            if not st.session_state.selection_areas:
                temp_image, center_pos = draw_selection_box(st.session_state.base_image)
                st.session_state.current_image = temp_image
                st.session_state.current_box_position = center_pos
        st.rerun()
    
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
        # 更新当前鼠标位置的选择框
        current_point = (coordinates["x"], coordinates["y"])
        temp_image, new_pos = draw_selection_box(st.session_state.base_image, current_point)
        st.session_state.current_image = temp_image
        st.session_state.current_box_position = new_pos
        
        # 当点击时添加/更新选择区域
        if st.button("📌 确认选择区域"):
            st.session_state.selection_areas = [get_selection_coordinates(
                st.session_state.current_box_position, 
                (st.session_state.base_image.width, st.session_state.base_image.height)
            )]
            st.rerun()
    
    # 显示已选择的区域状态
    if st.session_state.selection_areas:
        st.markdown("**✅ 已选择区域**")
        
        # 清除选择按钮
        if st.button("🗑️ 清除选择区域"):
            st.session_state.selection_areas = []
            # 清除选择后恢复到中心位置
            temp_image, center_pos = draw_selection_box(st.session_state.base_image)
            st.session_state.current_image = temp_image
            st.session_state.current_box_position = center_pos
            st.rerun()

with col2:
    st.markdown("## 设计参数")
    
    # 用户输入个性化参数
    theme = st.text_input("主题或关键词 (必填)", "花卉图案")
    
    # AI定制组和预设设计组的不同处理
    if st.session_state.experiment_group:  # AI定制组
        style = st.text_input("设计风格", "abstract")
        colors = st.text_input("偏好颜色", "pink, gold")
        details = st.text_area("更多细节", "some swirling shapes")
        
        # 生成设计按钮
        if st.button("🎨 生成AI设计"):
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
                        st.rerun()
                    else:
                        st.error("生成图像失败，请稍后重试。")
    else:  # 预设设计组
        # 提供预设设计选择
        available_designs = list(PRESET_DESIGNS.keys())
        selected_design = st.selectbox("选择预设设计", available_designs)
        
        # 应用预设设计按钮
        if st.button("🎨 应用预设设计"):
            if not st.session_state.selection_areas:
                st.warning("请先在T恤上选择至少一个区域！")
            else:
                # 模拟加载预设设计
                with st.spinner("正在应用预设设计..."):
                    try:
                        # 实际项目中，应该准备好这些预设设计文件
                        # 在此示例中，我们使用AI生成作为模拟
                        preset_prompt = f"Create a {selected_design} t-shirt design with transparent background, simple and clean style"
                        preset_design = generate_vector_image(preset_prompt)
                        
                        if preset_design:
                            st.session_state.generated_design = preset_design
                            
                            # 在原图上合成
                            composite_image = st.session_state.base_image.copy()
                            
                            # 遍历所有选择区域，将设计图放置到每个区域
                            for area in st.session_state.selection_areas:
                                left, top, width, height = area
                                
                                # 将生成图案缩放到选择区域大小
                                if width > 0 and height > 0:  # 确保区域有效
                                    scaled_design = preset_design.resize((width, height), Image.LANCZOS)
                                    
                                    try:
                                        # 确保使用透明通道进行粘贴
                                        composite_image.paste(scaled_design, (left, top), scaled_design)
                                    except Exception as e:
                                        st.warning(f"使用透明通道粘贴失败，直接粘贴: {e}")
                                        composite_image.paste(scaled_design, (left, top))
                            
                            st.session_state.final_design = composite_image
                            st.rerun()
                        else:
                            st.error("应用预设设计失败，请稍后重试。")
                    except Exception as e:
                        st.error(f"应用预设设计时出错: {e}")
                        
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

# 如果已生成最终设计，显示购买意向调查
if st.session_state.final_design is not None and not st.session_state.submitted:
    st.markdown("---")
    st.markdown("## 您的反馈")
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
    
    # 定制体验难度
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
            'experiment_group': "AI定制组" if st.session_state.experiment_group else "预设设计组",
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'design_duration': round(design_duration, 2),
            'purchase_intent': purchase_intent,
            'satisfaction_score': satisfaction_score,
            'customize_difficulty': customize_difficulty,
            'price_willing_to_pay': price_willing_to_pay,
            'theme': theme,
            'style': style if st.session_state.experiment_group else selected_design,
            'colors': colors if st.session_state.experiment_group else "",
            'details': details if st.session_state.experiment_group else "",
            'feedback': feedback
        }
        
        # 保存数据
        if save_experiment_data(experiment_data):
            st.session_state.submitted = True
            st.success("感谢您的反馈！您的数据已被记录，将有助于我们的研究。")
            st.rerun()
        else:
            st.error("保存反馈数据失败，请重试。")
    
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

# 页脚
st.markdown("---")
st.markdown("### 实验说明")
st.markdown("""
本实验旨在研究AI定制服装对消费者购买行为的影响。

**实验流程**：
1. 您将被随机分配到AI定制组或预设设计组
2. 按照界面提示完成T恤定制
3. 完成满意度和购买意向调查

**实验目的**：
- 了解AI定制功能如何影响消费者的购买决策
- 探索服装定制体验与消费者满意度的关系
- 分析不同定制方式与消费者愿意支付价格的关联

参与本实验的所有数据仅用于学术研究，我们将对您的信息严格保密。
感谢您的参与！
""")
