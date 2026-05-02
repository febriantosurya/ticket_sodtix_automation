import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os
import sys
import time
import re

INFO_FILE = "info.json"

INFO_TEMPLATE = {
    "buyer": {
        "full_name": "# Your Name",
        "number": "# 08xxxxxxxx",
        "email": "# example@example.com"
    },
    "ticket_holders": [
        {
            "full_name": "# Your Name",
            "number": "# 08xxxxxxxx",
            "gender": "# Male/Female",
            "dob": "# DD/MM/YYYY",
            "ktp": "# [KTP Number]"
        }
    ]
}


def load_info():
    if not os.path.exists(INFO_FILE):
        with open(INFO_FILE, "w") as f:
            json.dump(INFO_TEMPLATE, f, indent=2)
        print(f"[!] '{INFO_FILE}' created. Fill it in then re-run.")
        sys.exit(0)

    with open(INFO_FILE) as f:
        info = json.load(f)

    buyer = info.get("buyer", {})
    holders = info.get("ticket_holders", [])

    if not buyer.get("full_name") or not buyer.get("email"):
        print("[!] buyer info incomplete in info.json")
        sys.exit(1)
    if not holders or not holders[0].get("full_name"):
        print("[!] ticket_holders empty or incomplete in info.json")
        sys.exit(1)

    return info


def create_driver(headless=False, profile_dir=None, version_main=146):
    options = uc.ChromeOptions()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-images")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--dns-prefetch-disable")
    options.add_argument("--aggressive-cache-discard")

    if profile_dir:
        options.add_argument(f"--user-data-dir={profile_dir}")

    driver = uc.Chrome(options=options, use_subprocess=True, version_main=version_main)
    return driver


def wait_for(driver, by, selector, timeout=15, condition="clickable"):
    wait = WebDriverWait(driver, timeout, poll_frequency=0.05)
    cond_map = {
        "visible": EC.visibility_of_element_located,
        "clickable": EC.element_to_be_clickable,
        "present": EC.presence_of_element_located,
    }
    return wait.until(cond_map[condition]((by, selector)))


def fast_click(driver, element):
    driver.execute_script("arguments[0].click();", element)


def select_gender(driver, index, gender_value):
    try:
        combobox = driver.find_element(By.XPATH, f"//div[@id='mui-component-select-passengers.{index}.gender']")
    except Exception:
        return
    combobox.click()
    option = WebDriverWait(driver, 5, poll_frequency=0.05).until(
        EC.element_to_be_clickable((By.XPATH, f"//ul[@role='listbox']//li[normalize-space(text())='{gender_value}']"))
    )
    option.click()


def fill_form(driver, info, checkout_code=None):
    buyer = info["buyer"]
    holders = info["ticket_holders"]
    print("[~] Waiting for form...")
    wait_for(driver, By.NAME, "orderInfo.name", condition="present")
    print("[~] Form loaded. Filling buyer info...")

    fields = {
        "orderInfo.name": buyer["full_name"],
        "orderInfo.phone": buyer["number"].lstrip("0"),
        "orderInfo.email": buyer["email"],
        "orderInfo.emailConfirmation": buyer["email"],
    }
    for i, holder in enumerate(holders):
        fields[f"passengers.{i}.name"] = holder["full_name"]
        fields[f"passengers.{i}.phone"] = holder["number"].lstrip("0")
        fields[f"passengers.{i}.date_of_birth"] = holder["dob"]
        if holder.get("ktp"):
            fields[f"passengers.{i}.identity_number"] = holder["ktp"]
        print(f"[~] Holder {i+1}: {holder['full_name']}")

    driver.execute_script("""
        var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        var fields = arguments[0];
        for (var name in fields) {
            var el = document.querySelector('input[name="' + name + '"]');
            if (el) {
                setter.call(el, fields[name]);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
    """, fields)
    print("[~] Fields filled.")

    for i, holder in enumerate(holders):
        print(f"[~] Selecting gender for holder {i+1}: {holder['gender']}")
        select_gender(driver, i, holder["gender"])


    if checkout_code:
        print(f"[~] Entering voucher code: {checkout_code}")
        driver.execute_script("""
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            var el = document.querySelector('input[name="voucher"]');
            if (el) {
                setter.call(el, arguments[0]);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        """, checkout_code)
        apply_btn = wait_for(driver, By.XPATH, "//button[normalize-space(text())='USE']", condition="clickable")
        fast_click(driver, apply_btn)
        time.sleep(0.5)
        voucher_input = driver.find_element(By.NAME, "voucher")
        if voucher_input.get_attribute("aria-invalid") == "true":
            print("[!] Voucher code invalid — continuing without discount.")
        else:
            print("[~] Voucher applied.")

    print("[~] Checking agreement...")
    agree_input = driver.find_element(By.NAME, "is_aggree")
    if not agree_input.is_selected():
        fast_click(driver, agree_input)

    print("[~] Submitting form...")
    submit = wait_for(driver, By.CSS_SELECTOR, "button[type='submit']", condition="clickable")
    fast_click(driver, submit)


def open_browser(version_main=146):
    driver = create_driver(headless=False, version_main=version_main)
    print("[✓] Browser ready.")
    return driver


def find_and_click_sodtix_redirect(driver, user_choice):
    # driver already on band site — no driver.get() here                                                                                                                                    
                                                                                                                                                                                            
    redirect_buttons = driver.find_elements(                                                                                                                                                
        By.XPATH,                                                                                                                                                                           
        "//*[self::a or self::button]["
        "(contains(@href, 'sodtix.com') and not(contains(@href, 'mailto:'))) or "
        "(contains(@onclick, 'sodtix.com') and not(contains(@onclick, 'mailto:'))) or "                                                                                                     
        "(contains(@data-url, 'sodtix.com') and not(contains(@data-url, 'mailto:')))]"
    )                                                                                                                                                                                       
        
    if not redirect_buttons:                                                                                                                                                                
        print("[!] No sodtix redirect buttons found")
        return False

    idx = 0 if user_choice == "ARTIST PRESALE" else 1                                                                                                                                       
    button = redirect_buttons[idx]
                                                                                                                                                                                            
    href = button.get_attribute("href")
    if href and "sodtix.com" in href:
        # direct link — just navigate                                                                                                                                                       
        driver.get(href)
        return True                                                                                                                                                                         
        
    onclick = button.get_attribute("onclick")                                                                                                                                               
    if onclick:
        for pattern in [                                                                                                                                                                    
            re.compile(r"window\.open\('([^']+)'"),
            re.compile(r"window\.location\.href\s*=\s*'([^']+)'"),
            re.compile(r"document\.location\s*=\s*'([^']+)'"),                                                                                                                              
        ]:
            match = pattern.search(onclick)                                                                                                                                                 
            if match:                                                                                                                                                                       
                driver.get(match.group(1))
                return True                                                                                                                                                                 
        
    # fallback: click and wait for new tab                                                                                                                                                  
    fast_click(driver, button)
    if len(driver.window_handles) > 1:                                                                                                                                                      
        driver.switch_to.window(driver.window_handles[-1])
    return True



def run(url, target_categories=None, stop_event=None, version_main=146, auto_proceed=False, driver=None, band_url=None, checkout_code=None, sale_type="ARTIST PRESALE"):
    info = load_info()
    qty = len(info["ticket_holders"])
    owns_driver = driver is None
    if owns_driver:
        driver = create_driver(headless=False, version_main=version_main)

    try:
        if band_url:
            print(f"[~] Navigating to band site: {band_url}")
            driver.get(band_url)
            print(f"[~] Band site title: {driver.title}")
            while True:
                if stop_event and stop_event.is_set():
                    print("[!] Stopped by user")
                    break
                
                find_and_click_sodtix_redirect(driver, sale_type)

                if driver.current_url == band_url:
                    print("[!] No redirect yet, retrying...")
                    time.sleep(1)
                    driver.refresh()
                else:
                    print(f"[✓] Redirected. Now on: {driver.current_url}")
                    break
        else:
            print(f"[~] Navigating to event page...")
            driver.get(url)
            print(f"[~] Title: {driver.title}")
            print(f"[~] URL:   {driver.current_url}")

        print(f"[~] Buying {qty} ticket(s)")
        print(f"[~] Target categories: {', '.join(target_categories)}")

        TARGET_CATEGORIES = target_categories

        selected = False
        while not selected:
            if stop_event and stop_event.is_set():
                print("[!] Stopped by user")
                break

            print("[~] Waiting for ticket cards...")
            wait_for(driver, By.CSS_SELECTOR, ".MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded.MuiPaper-elevation1.css-1k3k3kw", condition="present")

            last_count = 0
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                cards = driver.find_elements(By.CSS_SELECTOR, ".MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded.MuiPaper-elevation1.css-1k3k3kw")
                if len(cards) == last_count:
                    break
                last_count = len(cards)
            print(f"[~] Found {last_count} ticket card(s). Scanning...")

            driver.execute_script("window.scrollTo(0, 0);")

            refresh_triggered = False
            all_sold_out = True

            for target in TARGET_CATEGORIES:
                for card in cards:
                    h6s = card.find_elements(By.CSS_SELECTOR, ".MuiTypography-root.MuiTypography-h6.css-40rwpa")
                    if not h6s or target.lower() not in h6s[0].text.lower():
                        continue
                    label = h6s[0].text
                    btn_add_1 = card.find_element(By.TAG_NAME, "button")

                    if btn_add_1.text == "Sold Out":
                        print(f"  [SOLD OUT] {label} — trying next target")
                        break
                    elif not btn_add_1.is_enabled():
                        print(f"  [NOT OPEN] {label} — refreshing...")
                        all_sold_out = False
                        refresh_triggered = True
                        break
                    else:
                        print(f"  [AVAILABLE] {label} — adding {qty} ticket(s)")
                        all_sold_out = False
                        grandparent = driver.execute_script(
                            "return arguments[0].parentElement.parentElement;", h6s[0]
                        )
                        btn = grandparent.find_element(By.TAG_NAME, "button")
                        fast_click(driver, btn)
                        for _ in range(qty - 1):
                            btn_add = grandparent.find_elements(By.TAG_NAME, "button")
                            fast_click(driver, btn_add[1])
                        selected = True
                        break
                if selected or refresh_triggered:
                    break

            if all_sold_out:
                print("[!] All target categories sold out")
                break
            if refresh_triggered:
                driver.refresh()

        if selected:
            print("[~] Proceeding to checkout...")
            checkout_card = driver.find_element(By.CSS_SELECTOR, ".MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded.MuiPaper-elevation1.css-1ddopcr")
            checkout_btn = checkout_card.find_element(By.TAG_NAME, "button")
            fast_click(driver, checkout_btn)

            print("[~] Expanding ticket holder forms...")
            wait_for(driver, By.CSS_SELECTOR, ".MuiAccordionSummary-root", condition="clickable")
            for accordion in driver.find_elements(By.CSS_SELECTOR, ".MuiAccordionSummary-root"):
                if accordion.get_attribute("aria-expanded") != "true":
                    fast_click(driver, accordion)

            fill_form(driver, info, checkout_code)

            if auto_proceed:
                print("[~] Waiting for payment dialog...")
                dialog = wait_for(driver, By.CSS_SELECTOR, ".MuiDialog-paper", condition="present")
                proceed_btn = dialog.find_elements(By.TAG_NAME, "button")[-1]
                fast_click(driver, proceed_btn)
                print("[~] Proceeded to payment.")

        print("\n[✓] Done! Browser open. Click Stop/Quit to close.")
        if stop_event:
            stop_event.wait()
        else:
            try:
                input("Press Enter to close the browser...")
            except (EOFError, KeyboardInterrupt):
                pass

    finally:
        if owns_driver:
            driver.quit()


if __name__ == "__main__":
    # band_url = "https://theneighbourhoodjakarta.com/"
    # checkout_code = "testing"
    # band_url = "https://5sosjakarta.com/"
    band_url = input("Band URL (leave empty if event url): ").strip()
    checkout_code = input("Checkout Code (leave empty to skip): ").strip()
    url = input("Event URL (leave empty if using band url): ").strip()
    cats = [c.strip() for c in input("Target categories (comma-separated): ").split(",") if c.strip()]
    ver = input("Chrome version (default 146): ").strip()
    run(url, cats, version_main=int(ver) if ver else 146, band_url=band_url, checkout_code=checkout_code)
