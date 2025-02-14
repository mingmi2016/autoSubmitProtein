from playwright.sync_api import sync_playwright
import time
import os
import tempfile
import shutil

def get_chrome_user_data_dir():
    """获取 Chrome 用户数据目录"""
    return os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")

def create_temp_profile(original_profile):
    """创建临时配置文件目录"""
    temp_dir = tempfile.mkdtemp(prefix="chrome_temp_")
    
    try:
        # 复制必要的配置文件
        default_dir = os.path.join(original_profile, "Default")
        temp_default_dir = os.path.join(temp_dir, "Default")
        os.makedirs(temp_default_dir)
        
        files_to_copy = ["Preferences", "Bookmarks", "Favicons", "History"]
        for file in files_to_copy:
            src = os.path.join(default_dir, file)
            dst = os.path.join(temp_default_dir, file)
            if os.path.exists(src):
                shutil.copy2(src, dst)
    except Exception as e:
        print(f"复制配置文件时出错: {e}")
    
    return temp_dir

def read_sequences(file_path):
    """读取序列文件"""
    sequences = []
    with open(file_path, 'r') as f:
        lines = f.readlines()
        
    current_name = None
    current_seq = None
    
    for line in lines:
        line = line.strip()
        if not line:  # 跳过空行
            if current_name and current_seq:
                sequences.append((current_name, current_seq))
                current_name = None
                current_seq = None
        elif not current_name:
            current_name = line
        else:
            current_seq = line
            
    # 添加最后一个序列
    if current_name and current_seq:
        sequences.append((current_name, current_seq))
        
    return sequences

def submit_sequences():
    # 读取序列文件
    sequences = read_sequences('JUNCE.txt')
    if not sequences:
        print("错误：无法读取序列文件或文件为空")
        return False
    
    print(f"读取到 {len(sequences)} 个序列")
    
    # 获取 Chrome 用户数据目录
    original_profile = get_chrome_user_data_dir()
    if not os.path.exists(original_profile):
        print("错误：找不到 Chrome 用户数据目录")
        return False
    
    # 创建临时配置文件
    temp_dir = create_temp_profile(original_profile)
    
    try:
        with sync_playwright() as p:
            try:
                # 启动 Chrome 浏览器
                print("启动 Chrome 浏览器...")
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=temp_dir,
                    executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    headless=False,
                    ignore_default_args=["--enable-automation"],
                    args=[
                        '--start-maximized',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-blink-features=AutomationControlled'
                    ]
                )
                
                page = browser.new_page()
                
                # 修改 navigator.webdriver
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                # 访问网站
                print("正在访问 AlphaFold Server...")
                page.goto("https://alphafoldserver.com/", timeout=60000)
                time.sleep(2)
                
                # 等待并点击登录按钮
                print("等待登录...")
                login_button = page.locator('span:has-text("Continue with Google")')
                if login_button.is_visible():
                    login_button.click()
                    print("\n请在浏览器中完成 Google 登录。")
                    print("完成后请按回车键继续...")
                    input()
                    time.sleep(3)  # 给页面更多加载时间
                
                # 检查 Add entity 按钮
                print("检查 Add entity 按钮...")
                # 使用更具体的选择器
                add_button = page.locator('button.new-sequence.mdc-button')
                
                max_retries = 3
                for i in range(max_retries):
                    try:
                        if add_button.is_visible(timeout=5000):
                            break
                        print(f"尝试 {i+1}/{max_retries}: 等待 Add entity 按钮出现...")
                        time.sleep(2)
                    except Exception as e:
                        print(f"尝试 {i+1} 失败: {e}")
                        if i == max_retries - 1:
                            raise
                
                if not add_button.is_visible():
                    print("错误：无法找到 Add entity 按钮，请确保已登录")
                    # 打印页面内容以便调试
                    print("\n当前页面内容:")
                    print(page.content())
                    return False
                
                print("找到 Add entity 按钮！")
                
                # 提交序列
                for name, sequence in sequences:
                    print(f"\n正在提交序列: {name}")
                    
                    # 点击 Add entity 按钮
                    add_button.click()
                    time.sleep(1)
                    
                    # 等待新的序列输入框出现并定位到最后一个
                    sequence_input = page.locator('textarea.sequence-input').last
                    if not sequence_input.is_visible(timeout=5000):
                        print(f"错误：无法找到序列输入框 - {name}")
                        continue
                    
                    def input_sequence(retry=False):
                        if retry:
                            print("重试：清除并重新输入序列...")
                            # 点击 Clear 按钮
                            clear_button = page.locator('button:has-text("Clear")')
                            if clear_button.is_visible():
                                clear_button.click()
                                time.sleep(1)
                        
                        # 先输入前4个字符，模拟手动输入
                        print("输入前4个字符...")
                        sequence_input.click()  # 确保焦点在正确的输入框上
                        
                        # 一个一个字符输入，模拟真实输入速度
                        for i in range(4):
                            sequence_input.type(sequence[i], delay=200)  # 每个字符输入延迟200ms
                            print(f"已输入: {sequence[i]}")
                            time.sleep(0.3)  # 字符之间额外等待0.3秒
                        
                        time.sleep(1)  # 等待序列验证
                        
                        # 检查 Save job 按钮状态
                        save_button = page.locator('button:has-text("Save job")')
                        print("检查 Save job 按钮状态...")
                        
                        def is_button_enabled():
                            # 检查按钮是否有 disabled 属性
                            return not save_button.get_attribute('disabled')
                        
                        if not is_button_enabled():
                            if not retry:  # 如果是第一次尝试，就重试一次
                                return input_sequence(retry=True)
                            return False
                        
                        # 输入剩余序列，也模拟手动输入
                        print("输入剩余序列...")
                        sequence_input.click()  # 再次确保焦点
                        remaining_sequence = sequence[4:]
                        
                        # 分批输入剩余序列，每批10个字符
                        chunk_size = 10
                        for i in range(0, len(remaining_sequence), chunk_size):
                            chunk = remaining_sequence[i:i+chunk_size]
                            sequence_input.type(chunk, delay=100)  # 每个字符延迟100ms
                            time.sleep(0.2)  # 每个块之间等待0.2秒
                        
                        time.sleep(1)  # 等待序列验证
                        return True
                    
                    # 输入序列
                    print(f"正在输入序列...")
                    
                    # 等待新的序列输入框出现并定位到最后一个
                    sequence_input = page.locator('textarea.sequence-input').last
                    if not sequence_input.is_visible(timeout=5000):
                        print(f"错误：无法找到序列输入框 - {name}")
                        continue
                    
                    # 尝试输入序列
                    if not input_sequence():
                        print("错误：无法启用 Save job 按钮")
                        continue
                    
                    print("Save job 按钮已可用")
                    time.sleep(1)
                    
                    try:
                        save_button.click(timeout=5000)
                    except Exception as e:
                        print(f"点击 Save job 按钮失败: {e}")
                        print("尝试使用 JavaScript 点击...")
                        page.evaluate('document.querySelector("button:has-text(\'Save job\')").click()')
                    
                    time.sleep(2)
                    
                    # 等待对话框出现
                    dialog = page.locator('gdm-af-preview-dialog')
                    if not dialog.is_visible(timeout=5000):
                        print("错误：无法找到保存对话框")
                        continue
                    
                    # 输入 Job name - 使用更精确的选择器
                    job_name_input = page.locator('input[aria-label="Job name"]')
                    if not job_name_input.is_visible(timeout=5000):
                        print("错误：无法找到 Job name 输入框")
                        continue
                    
                    job_name_input.fill(name)
                    time.sleep(1)
                    
                    # 点击 Seed 开关
                    seed_toggle = page.locator('mat-slide-toggle.seed-toggle')
                    if seed_toggle.is_visible():
                        seed_toggle.click()
                        time.sleep(1)
                    
                    # 点击对话框中的 Save job 按钮
                    confirm_button = page.locator('button.confirm')
                    if not confirm_button.is_visible(timeout=5000):
                        print("错误：无法找到确认按钮")
                        continue
                    
                    confirm_button.click()
                    time.sleep(2)  # 等待保存完成
                    
                    print(f"序列 {name} 已保存")
                
                print("\n所有序列已提交完成！")
                print("按回车键关闭浏览器...")
                input()
                return True
                
            except Exception as e:
                print(f"发生错误: {e}")
                return False
            finally:
                if 'browser' in locals():
                    browser.close()
    finally:
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

if __name__ == "__main__":
    submit_sequences()
