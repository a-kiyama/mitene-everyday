import sys, os, time, configparser, random, logging
from datetime import datetime as dt
import urllib.request
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException

class GUI(tk.Frame):
    def __init__(self, master = None):
        super().__init__(master)
        os.makedirs('log', exist_ok=True)
        logging.basicConfig(filename='log/main.log', level=logging.INFO)
        self.master = master
        self.master.geometry('640x200')
        self.driver = None
        self.master.protocol('WM_DELETE_WINDOW', self.on_closing)
        
        self.config_ini = configparser.ConfigParser()
        self.config_ini.read('config.ini', encoding='utf-8')
        self.set_slideshow_widget()
        self.set_widget()

    def set_slideshow_widget(self):
        config_width = int(self.config_ini['Config']['Width'])
        config_height = int(self.config_ini['Config']['Height'])
        self.content_window = tk.Toplevel(self.master)
        self.content_window.withdraw()
        self.content_window.geometry('%dx%d' % (config_width, config_height))
        self.slide_show = SlideShow(master = self.content_window)
        self.slide_show.set_canvas(config_width, config_height)
        self.img_list = self.load_image_list()
        self.slide_show.update_image_list(self.img_list)
        
    def set_widget(self):
        config_url = self.config_ini['Config']['Url']
        config_pass = self.config_ini['Config']['Password']
        self.url_label = tk.Label(self.master, text = 'URL')
        self.url_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.url_input = tk.Entry(width = 40)
        self.url_input.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.url_input.insert(0, config_url)
        self.password_label = tk.Label(self.master, text = 'Password')
        self.password_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.password_input = tk.Entry(width = 30, show = '*')
        self.password_input.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.password_input.insert(0, config_pass)
        self.start_button = tk.Button(self.master, text = 'Start', command = self.start_slide_show)
        self.start_button.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.stop_button = tk.Button(self.master, text = 'Stop', command = self.stop_slide_show)
        self.stop_button.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        self.stop_button.grid_forget()
        
    def start_slide_show(self):
        self.content_window.deiconify()
        self.auto_update()
        self.auto_fetch()
        self.start_button.grid_forget()
        self.stop_button.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

    def stop_slide_show(self):
        self.content_window.withdraw()
        self.after_cancel(self.next_update)
        self.after_cancel(self.next_fetch)
        self.stop_button.grid_forget()
        self.start_button.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
    
    def load_image_list(self):
        size = int(self.config_ini['Config']['Length'])
        image_list = list()
        os.makedirs('img', exist_ok=True)
        for i in range(size):
            try:
                image = Image.open('img/%d.png' % i)
                image_list.append(image)
            except FileNotFoundError:
                if len(image_list) > 0:
                    return image_list
                else:
                    return None
        return image_list

    def setup_driver(self):
        try:
            options = Options()
            options.add_argument('--headless')
            driver = webdriver.Chrome(options=options)
        except WebDriverException:
            logging.error('%s: Chrome web driver not installed' % dt.now())
            sys.exit(1)
        return driver

    def fetch_images(self):
        if self.driver == None:
            self.driver = self.setup_driver()
        img_url_list = self.get_img_urls()
        for img_url in img_url_list:
            savename = 'img/%s.png' % str(img_url_list.index(img_url))
            urllib.request.urlretrieve(img_url, savename)
            logging.debug('%s: %s has been fetched' % (dt.now(), savename))
        self.img_list = self.load_image_list()
        logging.info('%s: %d files have been fetched' % (dt.now(), len(self.img_list)))
        self.slide_show.update_image_list(self.img_list)

    def get_img_urls(self):
        size = int(self.config_ini['Config']['Length'])
        url = self.url_input.get()
        password = self.password_input.get()
        self.driver.get(url)
        if self.driver.current_url.split('/')[-1] == 'login':
            pw_input = self.driver.find_element_by_id('session_password')
            pw_input.send_keys(password)
            pw_input.send_keys(Keys.ENTER)
        first = self.driver.find_elements_by_class_name('media-thumbnail-container')[0]
        first.click()
        image_urls = []
        i = 0
        while i < size:
            img = self.driver.find_element_by_id('media-img')
            img_url = img.get_attribute('src')
            img_style = img.get_attribute('style')
            if img_style != 'display: none;':
                image_urls.append(img_url)
                i += 1
            self.driver.find_element_by_class_name('next-button').click()
            time.sleep(0.5)
        return image_urls

    def auto_update(self):
        config_interval = int(self.config_ini['Config']['Interval'])
        if config_interval <= 0:
            config_interval = 1
        th = threading.Thread(target=self.update)
        th.start()
        self.next_update = self.after(config_interval * 1000, self.auto_update)

    def auto_fetch(self):
        th = threading.Thread(target=self.fetch_images)
        th.start()
        self.next_fetch = self.after(24 * 3600 * 1000, self.auto_fetch)

    def update(self):
        if self.slide_show == None or self.img_list == None:
            return
        self.slide_show.load_next()

    def on_closing(self):
        if messagebox.askokcancel('Quit', 'Do you want to quit?'):
            if self.driver != None:
                self.driver.quit()
            self.master.destroy()

class SlideShow(tk.Frame):
    def __init__(self, master = None):
        super().__init__(master)
        self.master = master
        self.master.title('Slide Show')
        self.img_list = [None, None]
        self.content = None
        self.active_bank = 1
        self.ptr = 0
        self.master.protocol('WM_DELETE_WINDOW', self.on_closing)

    def set_canvas(self, width, height):
        self.content = tk.Canvas(self.master, bg='black', width=width, height=height)
        self.content.pack(expand=1, fill='both')
        w = self.content.winfo_width()
        h = self.content.winfo_height()
        self.image_on_canvas = self.content.create_image(0, 0, image=None, anchor='nw')

    def update_image_list(self, img_list):
        if img_list == None:
            return
        self.active_bank = 1 - self.active_bank
        self.img_list[self.active_bank] = img_list
        random.shuffle(self.img_list[self.active_bank])
        self.ptr = 0
        self.num = len(img_list)

    def load_next(self):
        if self.img_list[self.active_bank] == None or self.content == None:
            return
        w = self.content.winfo_width()
        h = self.content.winfo_height()
        image = self.img_list[self.active_bank][self.ptr]
        self.photo_image = ImageTk.PhotoImage(self.resize(image))
        self.content.itemconfig(self.image_on_canvas, image=self.photo_image, anchor='nw')
        self.ptr = (self.ptr + 1) % self.num
        if self.ptr == 0:
            random.shuffle(self.img_list[self.active_bank])

    def resize(self, image):
        w, h = image.width, image.height
        win_w = self.content.winfo_width()
        win_h = self.content.winfo_height()
        base_w = win_w
        base_h = int(h * win_w / w)
        new_w = base_w if base_h <= win_h else int(w * win_h / h)
        new_h = base_h if base_h <= win_h else win_h
        return image.resize((new_w, new_h))
       
    def on_closing(self):
        messagebox.showinfo('Info', 'Please click "Stop" button to stop slide show')

if __name__ == '__main__':
    gui = tk.Tk()
    app = GUI(master = gui)
    app.mainloop()
