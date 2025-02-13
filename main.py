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
                page.goto("https://alphafold.ebi.ac.uk/", timeout=60000)
                time.sleep(2)
                
                # 等待并点击登录按钮
                print("等待登录...")
                login_button = page.locator('span:has-text("Continue with Google")')
                if login_button.is_visible():
                    login_button.click()
                    print("\n请在浏览器中完成 Google 登录。")
                    print("完成后请按回车键继续...")
                    input()
                
                # 检查 Add entity 按钮
                print("检查 Add entity 按钮...")
                add_button = page.locator('span:has-text("Add entity")')
                
                if not add_button.is_visible(timeout=5000):
                    print("错误：无法找到 Add entity 按钮，请确保已登录")
                    return False
                
                # 提交序列
                for name, sequence in sequences:
                    print(f"\n正在提交序列: {name}")
                    
                    # 点击 Add entity 按钮
                    add_button.click()
                    time.sleep(1)
                    
                    # 等待新的序列输入框出现
                    sequence_input = page.locator('textarea.sequence-input').last
                    if not sequence_input.is_visible(timeout=5000):
                        print(f"错误：无法找到序列输入框 - {name}")
                        continue
                    
                    # 输入序列
                    sequence_input.fill(sequence)
                    print(f"已输入序列（长度：{len(sequence)}）")
                    time.sleep(1)
                
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
