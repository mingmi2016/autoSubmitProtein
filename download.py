import os
import time
import tempfile
import shutil
from playwright.sync_api import sync_playwright

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
    """读取序列文件中的名称"""
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    # 解析序列名称
    names = []
    i = 0
    while i < len(lines):
        name = lines[i]
        if i + 1 < len(lines):
            names.append(name)
            i += 2
        else:
            print(f"\n警告：第 {i+1} 行没有对应的序列")
            break
    
    print(f"\n从文件中读取到 {len(names)} 个任务名称")
    return names

def launch_browser(temp_dir):
    """启动 Chrome 浏览器"""
    print("启动 Chrome 浏览器...")
    with sync_playwright() as p:
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
        return browser

def login(page):
    """登录 AlphaFold Server"""
    print("等待登录...")
    login_button = page.locator('span:has-text("Continue with Google")')
    if login_button.is_visible():
        login_button.click()
        print("\n请在浏览器中完成 Google 登录。")
        print("完成后请按回车键继续...")
        input()
        time.sleep(3)  # 给页面更多加载时间
    else:
        print("已经登录，继续执行...")

def filter_tasks(page):
    """过滤任务"""
    print("点击过滤按钮...")
    filter_buttons = [
        'Saved draft',
        'In progress',
        'Examples',
        'Failed'
    ]
    for button_text in filter_buttons:
        try:
            # 使用JavaScript点击，因为按钮可能有复杂的嵌套结构
            page.evaluate(f'''() => {{
                const buttons = Array.from(document.querySelectorAll('span.mdc-evolution-chip__text-label'));
                const button = buttons.find(b => b.textContent.trim().includes('{button_text}'));
                if (button) {{
                    button.click();
                    console.log('Clicked {button_text}');
                }} else {{
                    console.log('Button not found: {button_text}');
                }}
            }}''')
            print(f"点击 {button_text} 按钮")
            time.sleep(1)  # 等待过滤效果
        except Exception as e:
            print(f"点击 {button_text} 按钮时出错: {e}")
            # 尝试使用常规方式点击
            try:
                button = page.locator(f'span.mdc-evolution-chip__text-label:has-text("{button_text}")')
                if button.is_visible(timeout=2000):
                    button.click()
                    print(f"使用常规方式点击 {button_text} 按钮")
                    time.sleep(1)
            except Exception as e:
                print(f"常规点击也失败: {e}")

def get_task_names(page):
    """获取任务名称"""
    task_table = page.locator('table.mat-mdc-table')
    task_table.wait_for(state='visible', timeout=10000)
    rows = task_table.locator('tbody tr')
    row_count = rows.count()
    print(f"找到 {row_count} 个任务")
    print("\n表格中的任务名称：")
    task_names = []
    for i in range(row_count):
        try:
            row = rows.nth(i)
            task_name_cell = row.locator('td.mat-column-name')
            if task_name_cell.is_visible(timeout=2000):
                task_name = task_name_cell.text_content().strip()
                task_names.append(task_name)
                print(f"- {task_name}")
        except Exception as e:
            print(f"获取第 {i+1} 行任务名称时出错: {e}")
    return task_names

def download_tasks(page, task_names):
    """下载任务"""
    print("\n开始处理任务...")
    rows = page.locator('tbody tr')
    row_count = rows.count()
    for i in range(row_count):
        try:
            row = rows.nth(i)
            task_name_cell = row.locator('td.mat-column-name')
            if not task_name_cell.is_visible(timeout=2000):
                print(f"第 {i+1} 行的任务名称单元格不可见")
                continue
            task_name = task_name_cell.text_content().strip()
            if task_name not in task_names:
                print(f"跳过任务 {task_name}，因为不在JUNCE.txt中")
                continue
                
            print(f"处理任务: {task_name}")
            
            # 首先点击更多操作按钮（三个点的图标按钮）
            more_button = row.locator('button.mat-mdc-menu-trigger.fold-actions')
            if more_button.is_visible(timeout=2000):
                more_button.click()
                time.sleep(1)  # 等待菜单出现
                
                # 等待下载按钮出现并点击
                download_button = page.locator('a.mat-mdc-menu-item[download]')
                if download_button.is_visible(timeout=2000):
                    # 开始下载
                    with page.expect_download() as download_info:
                        download_button.click()
                        download = download_info.value
                        
                        # 等待下载完成
                        print(f"等待下载 {task_name}...")
                        download.save_as(os.path.join(downloads_dir, f"{task_name}.zip"))
                        print(f"已下载: {task_name}")
                        time.sleep(2)  # 等待文件保存
                else:
                    print(f"找不到任务 {task_name} 的下载按钮")
            else:
                print(f"任务 {task_name} 的更多操作按钮不可见")
        except Exception as e:
            print(f"处理第 {i+1} 个任务时出错: {e}")

def download_results():
    # 读取需要下载的任务名称
    task_names = read_sequences('JUNCE.txt')
    if not task_names:
        print("错误：无法读取任务名称")
        return False
    
    # 获取 Chrome 用户数据目录
    original_profile = get_chrome_user_data_dir()
    if not os.path.exists(original_profile):
        print("错误：找不到 Chrome 用户数据目录")
        return False
    
    # 创建下载目录
    global downloads_dir
    downloads_dir = os.path.join(os.getcwd(), 'downloads')
    os.makedirs(downloads_dir, exist_ok=True)
    print(f"下载目录: {downloads_dir}")
    
    try:
        with sync_playwright() as p:
            # 启动 Chrome 浏览器
            print("启动 Chrome 浏览器...")
            browser = p.chromium.launch_persistent_context(
                user_data_dir=original_profile,  # 使用实际的用户配置
                executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                headless=False,
                ignore_default_args=["--enable-automation"],
                accept_downloads=True,
                args=[
                    '--start-maximized',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-blink-features=AutomationControlled',
                    f'--download.default_directory={downloads_dir}',
                    '--download.prompt_for_download=false',
                    '--disable-download-notification',
                    '--allow-file-access-from-files',  # 允许访问本地文件
                    '--allow-file-access',  # 允许文件访问
                    '--allow-running-insecure-content'  # 允许不安全内容
                ]
            )
            
            try:
                # 创建新页面并设置权限
                page = browser.new_page()
                context = browser
                context.grant_permissions(['geolocation'])
                
                # 修改 navigator.webdriver
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // 设置下载行为
                    Object.defineProperty(window, 'onbeforeunload', {
                        get: () => null,
                        set: () => {}
                    });
                """)
                
                # 访问 AlphaFold Server
                print("正在访问 AlphaFold Server...")
                page.goto("https://alphafoldserver.com/", wait_until='networkidle')
                time.sleep(3)
                
                # 登录
                login(page)
                time.sleep(3)
                
                # 过滤任务
                filter_tasks(page)
                time.sleep(2)
                
                # 获取任务名称
                table_task_names = get_task_names(page)
                
                # 下载任务
                download_tasks(page, task_names)
                
                print("\n所有下载任务完成！")
                print(f"文件已下载到: {downloads_dir}")
                print("按回车键关闭浏览器...")
                input()
                
            finally:
                browser.close()
                
    except Exception as e:
        print(f"运行过程中出错: {e}")
        return False
        
    return True

if __name__ == "__main__":
    download_results()
