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
    # 读取序列文件
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]  # 去除空行
    
    print(f"读取到 {len(lines)} 行非空数据")
    
    # 解析序列和名称
    sequences = []
    i = 0
    while i < len(lines):
        name = lines[i]
        if i + 1 < len(lines):
            sequence = lines[i + 1]
            print(f"\n发现序列 {len(sequences) + 1}:")
            print(f"名称: {name}")
            print(f"序列: {sequence[:20]}...")  # 只打印前20个字符
            sequences.append((name, sequence))
            i += 2
        else:
            print(f"\n警告：第 {i+1} 行没有对应的序列")
            break
    
    print(f"\n从文件中读取到 {len(sequences)} 个序列")
    return sequences

def submit_sequences():
    # 读取序列文件
    sequences = read_sequences('JUNCE.txt')
    
    print(f"从文件中读取到 {len(sequences)} 个序列")
    
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
                
                # 等待页面加载完成
                print("等待页面加载完成...")
                time.sleep(2)
                
                # 先点击 Clear 按钮清除可能存在的序列
                print("尝试清除现有序列...")
                try:
                    clear_button = page.locator('button:has-text("Clear")')
                    if clear_button.is_visible(timeout=5000):
                        clear_button.click()
                        print("已点击 Clear 按钮")
                        time.sleep(1)
                except Exception as e:
                    print(f"点击 Clear 按钮时出错: {e}")
                    # 尝试使用JavaScript点击
                    try:
                        page.evaluate('''() => {
                            const buttons = Array.from(document.querySelectorAll('button'));
                            const clearButton = buttons.find(button => 
                                button.querySelector('.mdc-button__label')?.textContent.trim() === 'Clear'
                            );
                            if (clearButton) clearButton.click();
                        }''')
                        print("已通过JavaScript点击 Clear 按钮")
                        time.sleep(1)
                    except Exception as e:
                        print(f"JavaScript点击也失败: {e}")
                
                # 检查 Add entity 按钮
                print("检查 Add entity 按钮...")
                add_button = page.locator('button:has-text("Add entity")')
                try:
                    add_button.wait_for(state='visible', timeout=5000)
                except Exception as e:
                    print(f"错误：无法找到 Add entity 按钮 - {e}")
                    return False
                
                print("找到 Add entity 按钮！")
                
                # 提交每个序列
                for name, sequence in sequences:
                    print(f"\n开始提交序列: {name}")
                    
                    try:
                        # 点击 Add entity 按钮
                        add_button = page.locator('button:has-text("Add entity")')
                        if not add_button.is_visible(timeout=5000):
                            print(f"错误：无法找到 Add entity 按钮")
                            continue
                        
                        add_button.click()
                        time.sleep(1)
                        
                        # 等待新的序列输入框出现并定位到最后一个
                        sequence_input = page.locator('textarea.sequence-input').last
                        if not sequence_input.is_visible(timeout=5000):
                            print(f"错误：无法找到序列输入框 - {name}")
                            continue
                        
                        save_button = page.locator('button:has-text("Save job")')
                        print("检查 Save job 按钮状态...")
                        
                        def is_button_enabled():
                            # 检查按钮是否有 disabled 属性
                            return not save_button.get_attribute('disabled')
                        
                        def input_sequence(retry=False):
                            nonlocal save_button  # 使用外部的 save_button 变量
                            
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
                                # sequence_input.type(chunk, delay=100)  # 每个字符延迟100ms
                                sequence_input.type(chunk)# 每个字符延迟100ms
                                # time.sleep(0.2)  # 每个块之间等待0.2秒
                            
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
                            # 点击第一个 Save job 按钮
                            # save_button.click(timeout=5000)
                            # print("已点击第一个 Save job 按钮")

                            continue_button = page.locator('span:has-text(" Continue and preview job ")')
                            continue_button.click()
                            
                            # 等待对话框出现
                            dialog = page.locator('gdm-af-preview-dialog')
                            dialog.wait_for(state='visible', timeout=5000)
                            print("对话框已出现")
                            
                            # 等待对话框中的输入框加载完成
                            print("等待输入框加载...")
                            try:
                                # 先尝试简单的选择器
                                job_name_input = dialog.locator('input[required]')
                                job_name_input.wait_for(state='visible', timeout=10000)
                                print("找到 Job name 输入框")
                            except Exception as e:
                                print(f"使用简单选择器失败: {e}")
                                # 如果失败，尝试使用JavaScript定位
                                print("尝试使用JavaScript定位输入框...")
                                page.evaluate('''() => {
                                    const inputs = Array.from(document.querySelectorAll('input'));
                                    const jobInput = inputs.find(input => 
                                        input.hasAttribute('required') && 
                                        input.classList.contains('mat-mdc-input-element')
                                    );
                                    if (jobInput) {
                                        jobInput.scrollIntoView();
                                        jobInput.focus();
                                    }
                                }''')
                                time.sleep(1)
                                
                                # 重新尝试定位已聚焦的输入框
                                job_name_input = dialog.locator('input:focus')
                                job_name_input.wait_for(state='visible', timeout=5000)
                                print("通过JavaScript找到输入框")
                            
                            # 生成作业名称（使用序列名称）
                            job_name = name
                            print(f"使用作业名称: {job_name}")
                            
                            # 先清除输入框
                            job_name_input.clear()
                            time.sleep(0.5)
                            
                            # 输入作业名称，使用type模拟真实输入
                            job_name_input.type(job_name, delay=100)
                            print(f"已输入作业名称: {job_name}")
                            time.sleep(1)
                            
                            # 点击 Seed 滑动开关
                            seed_toggle = dialog.locator('button.mdc-switch[role="switch"]')
                            seed_toggle.wait_for(state='visible', timeout=5000)
                            print("找到 Seed 滑动开关")
                            
                            # 检查当前状态
                            is_checked = seed_toggle.get_attribute('aria-checked') == 'true'
                            if not is_checked:
                                seed_toggle.click()
                                print("已启用 Seed 开关")
                                time.sleep(1)
                            
                            # # 等待输入框变为可用
                            # seed_input = dialog.locator('input[type="number"].seed-input')
                            # seed_input.wait_for(state='visible', timeout=5000)
                            
                            # # 输入种子值（如果需要的话）
                            # if seed_input.is_enabled():
                            #     seed_value = "1"  # 或者其他你想要的种子值
                            #     seed_input.fill(seed_value)
                            #     print(f"已输入种子值: {seed_value}")
                            #     time.sleep(1)
                            
                            # 点击对话框中的 Save job 按钮
                            # confirm_button = dialog.locator('button:has-text("Save job")')
                            # confirm_button.wait_for(state='visible', timeout=5000)
                            confirm_button = page.locator('span:has-text(" Confirm and submit job ")')
                            print("找到确认按钮")
                            
                            # 尝试直接点击
                            try:
                                confirm_button.click()
                                print("已点击确认按钮")
                            except Exception as e:
                                print(f"直接点击失败: {e}")
                                # print("尝试使用JavaScript点击...")
                                # # 使用JavaScript点击，通过文本内容定位按钮
                                # page.evaluate('''() => {
                                #     const buttons = Array.from(document.querySelectorAll('button'));
                                #     const saveButton = buttons.find(button => 
                                #         button.querySelector('.mdc-button__label')?.textContent.trim() === 'Save job'
                                #     );
                                #     if (saveButton) saveButton.click();
                                # }''')
                                # print("已通过JavaScript点击确认按钮")
                        
                        except Exception as e:
                            print(f"保存作业过程中出错: {e}")
                            continue
                        
                        time.sleep(6)
                        
                        # 等待对话框消失
                        dialog.wait_for(state='hidden', timeout=5000)
                        print("对话框已消失")
                        
                        print(f"序列 {name} 已保存")
                        
                        # 等待2秒
                        print("等待2秒...")
                        time.sleep(6)
                        
                        # 点击 Clear 按钮
                        print("点击 Clear 按钮...")
                        try:
                            clear_button = page.locator('button:has-text("Clear")')
                            clear_button.wait_for(state='visible', timeout=5000)
                            clear_button.click()
                            print("已点击 Clear 按钮")
                            
                            # 等待序列输入框清空
                            # time.sleep(1)
                            # sequence_input = page.locator('textarea.sequence-input').last
                            # if sequence_input.is_visible():
                            #     text = sequence_input.input_value()
                            #     if text:
                            #         print("警告：序列输入框未清空，尝试重新点击")
                            #         clear_button.click()
                            #         time.sleep(1)
                        except Exception as e:
                            print(f"点击 Clear 按钮时出错: {e}")
                            # 尝试使用JavaScript点击
                            try:
                                page.evaluate('''() => {
                                    const buttons = Array.from(document.querySelectorAll('button'));
                                    const clearButton = buttons.find(button => 
                                        button.querySelector('.mdc-button__label')?.textContent.trim() === 'Clear'
                                    );
                                    if (clearButton) clearButton.click();
                                }''')
                                print("已通过JavaScript点击 Clear 按钮")
                                time.sleep(1)
                            except Exception as e:
                                print(f"JavaScript点击也失败: {e}")
                        
                        # 再等待1秒确保清除完成
                        time.sleep(3)
                    
                    except Exception as e:
                        print(f"发生错误: {e}")
                        continue
                    
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
