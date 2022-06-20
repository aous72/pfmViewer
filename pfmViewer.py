import os

import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as msg

import numpy as np
import cv2
from PIL import Image, ImageTk

class myApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.image_loaded = False
        self.title('.pfm viewer')
        self.geometry('750x500')
        self.update()
        self.old_win_width = self.winfo_width()
        self.old_win_height = self.winfo_height()
        self.minsize(self.old_win_width, self.old_win_height)
        self.update()
        self.bind("<Configure>", self.onconfigure)

        # menu
        self.menubar = tk.Menu(self)

        # File menu
        self.filemenu = tk.Menu(self.menubar, tearoff=False)
        self.filemenu.add_command(label="Open...", accelerator='Ctrl-O', command=self.select_file, underline=0)
        self.filemenu.add_command(label="Save...", accelerator='Ctrl-S', command=self.save_file, underline=0,
                                  state=tk.DISABLED)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", accelerator='Ctrl-X', command=self.destroy, underline=1)
        self.menubar.add_cascade(label="File", menu=self.filemenu, underline=0)
        self.bind('<Control-o>', self.menu_shortcut)
        self.bind('<Control-s>', self.menu_shortcut)
        self.bind('<Control-x>', self.menu_shortcut)

        # zoom menu
        self.zoommenu = tk.Menu(self.menubar, tearoff=False)
        self.zoommenu.add_command(label="In", command=self.zoom_in, underline=0, accelerator='Z', state=tk.DISABLED)
        self.zoommenu.add_command(label="Out", command=self.zoom_out, underline=0, accelerator='Shift-Z',
                                  state=tk.DISABLED)
        self.menubar.add_cascade(label="Zoom", menu=self.zoommenu, underline=0)
        self.bind('<z>', self.menu_shortcut)
        self.bind('<Z>', self.menu_shortcut)
        self.zoom_multiplier = 1.0

        # About menu
        self.menubar.add_cascade(label="About", command=self.show_about_dialog, underline=0)

        # Add menu and show
        self.config(menu=self.menubar)

        # create one large label frame
        self.combined = tk.LabelFrame(self, borderwidth=0, highlightthickness=0)
        self.combined.grid(row=0, column=0, sticky=tk.NW)

        # Add checkboxes
        self.components = tk.LabelFrame(self.combined, text='Colour Components', labelanchor=tk.NW,\
                                        width=100, height=100)
        self.components.columnconfigure(0, weight=1)
        self.components.grid(row=0, column=0, padx=10, pady=10, sticky=tk.NW)
        self.components.grid_propagate(False)

        self.check_c0_var = tk.IntVar(self)
        self.check_c0 = tk.Checkbutton(self.components, text="C0", variable=self.check_c0_var, onvalue=1, offvalue=0,
                                       state=tk.DISABLED, command=self.show_image)
        self.check_c0.grid(row=0, sticky=tk.W)
        self.check_c1_var = tk.IntVar(self)
        self.check_c1 = tk.Checkbutton(self.components, text="C1", variable=self.check_c1_var, onvalue=1, offvalue=0,
                                       state=tk.DISABLED, command=self.show_image)
        self.check_c1.grid(row=1, sticky=tk.W)
        self.check_c2_var = tk.IntVar(self)
        self.check_c2 = tk.Checkbutton(self.components, text="C2", variable=self.check_c2_var, onvalue=1, offvalue=0,
                                       state=tk.DISABLED, command=self.show_image)
        self.check_c2.grid(row=2, sticky=tk.W)

        # Add scale entries
        self.curve = tk.LabelFrame(self.combined, text='Curve', labelanchor=tk.NW, width=100, height=180)
        self.curve.columnconfigure(0, weight=1)
        self.curve.grid(row=1, column=0, padx=10, pady=10, ipadx=10, ipady=5, sticky=tk.NW)
        self.curve.grid_propagate(False)

        tk.Label(self.curve, text='subtract:').grid(row=0, column=0)
        self.offset_str = tk.StringVar(self)
        self.offset_entry = tk.Entry(self.curve, width=10, textvariable=self.offset_str, state=tk.DISABLED)
        self.offset_entry.grid(row=1, column=0)
        self.offset_str.set('0.0')

        tk.Label(self.curve, text='divide by:').grid(row=2, column=0)
        self.scale_str = tk.StringVar(self)
        self.scale_entry = tk.Entry(self.curve, width=10, textvariable=self.scale_str, state=tk.DISABLED)
        self.scale_entry.grid(row=3, column=0)
        self.scale_str.set('1.0')

        tk.Label(self.curve, text='gamma').grid(row=4, column=0)
        self.gamma_str = tk.StringVar(self)
        self.gamma_entry = tk.Entry(self.curve, width=10, textvariable=self.gamma_str, state=tk.DISABLED)
        self.gamma_entry.grid(row=5, column=0)
        self.gamma_str.set('1.0')

        tk.Label(self.curve, text='').grid(row=6, column=0)
        self.update_btn = tk.Button(self.curve, text='Update', command=self.show_image, state=tk.DISABLED)
        self.update_btn.grid(row=7, column=0)

        # ranges
        self.ranges = tk.LabelFrame(self.combined, text='Range', labelanchor=tk.NW, width=100, height=100)
        self.ranges.columnconfigure(0, weight=1)
        self.ranges.grid(row=2, column=0, padx=10, pady=10, ipadx=10, ipady=5, sticky=tk.NW)
        self.ranges.grid_propagate(False)

        tk.Label(self.ranges, text='total').grid(row=0, column=0)
        self.total = tk.Label(self.ranges, text='[       -       ]')
        self.total.grid(row=1, column=0)
        tk.Label(self.ranges, text='current').grid(row=2, column=0)
        self.current = tk.Label(self.ranges, text='[       -       ]')
        self.current.grid(row=3, column=0)

        # image canvas
        self.image_box = tk.LabelFrame(self, borderwidth=0, highlightthickness=0)
        self.image_box.grid(row=0, column=1, sticky=tk.NW)

        self.hbar = tk.Scrollbar(self.image_box, orient=tk.HORIZONTAL)
        self.hbar.grid(row=1, column=0, sticky=tk.E+tk.W)
        self.vbar = tk.Scrollbar(self.image_box, orient=tk.VERTICAL)
        self.vbar.grid(row=0, column=1, sticky=tk.N+tk.S)

        self.image_canvas = tk.Canvas(self.image_box, width=self.old_win_width - 180, height=self.old_win_height - 50,
                                      scrollregion=(0,0,self.old_win_width - 180, self.old_win_height - 50))
        self.image_canvas.config(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)
        self.image_canvas.grid(row=0, column=0, sticky=tk.NW)

        self.hbar.config(command=self.image_canvas.xview)
        self.vbar.config(command=self.image_canvas.yview)

    def save_file(self):
        name = fd.asksaveasfilename(title='Save .png file', filetypes=[('.png files', '.png')])
        if name:
            head, tail = os.path.splitext(name)
            if not tail:
                name = name + ".png"
            cv2.imwrite(name, self.display_image)

    def select_file(self):
        name = fd.askopenfilename(title='Open .pfm file', filetypes=[('.pfm files', '.pfm')])
        if name:
            self.pfm_image = cv2.imread(name, cv2.IMREAD_UNCHANGED)
            if self.pfm_image is not None:
                self.show_image()

    def show_about_dialog(self):
        msg.showinfo('About...', '.pfm viewer version 0.0.1\nAuthor: Aous Naman')

    def show_image(self):
        if self.image_loaded == False:
            self.offset_entry.config(state=tk.NORMAL)
            self.scale_entry.config(state=tk.NORMAL)
            self.gamma_entry.config(state=tk.NORMAL)
            self.offset_str.set('0.0')
            self.scale_str.set('1.0')
            self.gamma_str.set('1.0')
            self.update_btn.config(state=tk.NORMAL)
            self.filemenu.entryconfig("Save...", state=tk.NORMAL)
            self.zoommenu.entryconfig("In", state=tk.NORMAL)
            self.zoommenu.entryconfig("Out", state=tk.NORMAL)
            self.image_loaded = True

        try:
            offset = float(self.offset_str.get())
        except ValueError as verr:
            self.offset_entry.config(bg='Red')
            return
        except Exception as ex:
            self.offset_entry.config(bg='Red')
            return
        self.offset_entry.config(bg='White')

        try:
            scale = float(self.scale_str.get())
        except ValueError as verr:
            self.scale_entry.config(bg='Red')
            return
        except Exception as ex:
            self.scale_entry.config(bg='Red')
            return
        if scale == 0.0:
            self.scale_entry.config(bg='Red')
            return
        else:
            self.scale_entry.config(bg='White')

        try:
            gamma = float(self.gamma_str.get())
        except ValueError as verr:
            self.gamma_entry.config(bg='Red')
            return
        except Exception as ex:
            self.gamma_entry.config(bg='Red')
            return
        self.gamma_entry.config(bg='White')

        total_max = self.pfm_image.max()
        total_min = self.pfm_image.min()
        t = "[" + "{: 7.3g}".format(total_min) + ' - ' + "{: 7.3g}".format(total_max) + "]"
        self.total.config(text=t)
        cur_max = offset + scale
        cur_min = offset
        t = "[" + "{: 7.3g}".format(cur_min) + ' - ' + "{: 7.3g}".format(cur_max) + "]"
        self.current.config(text=t)

        t = np.divide(np.subtract(self.pfm_image, offset), scale)
        s = np.sign(t)
        t = np.multiply(s, np.power(np.abs(t), 1.0/gamma))
        self.display_image = np.minimum(np.maximum(np.multiply(t, 255), 0), 255).astype(np.ubyte)
        if len(self.display_image.shape) == 2:  # one color
            self.check_c0.config(state=tk.DISABLED)
            self.check_c1.config(state=tk.DISABLED)
            self.check_c2.config(state=tk.DISABLED)
            self.check_c0_var.set(0)
            self.check_c1_var.set(0)
            self.check_c2_var.set(0)
            image = cv2.merge((self.display_image, self.display_image, self.display_image))
        else:  # 3 colours
            self.check_c0.config(state=tk.NORMAL)
            self.check_c1.config(state=tk.NORMAL)
            self.check_c2.config(state=tk.NORMAL)
            self.check_c0_var.set(1)
            self.check_c1_var.set(1)
            self.check_c2_var.set(1)
            blue, green, red = cv2.split(self.display_image)
            zero = np.zeros(red.shape, blue.dtype)
            if self.check_c0_var.get() == 0:
                red = zero
            if self.check_c1_var.get() == 0:
                green = zero
            if self.check_c2_var.get() == 0:
                blue = zero
            image = cv2.merge((red, green, blue))

        image = cv2.resize(image, np.flip(image.shape[0:2]) * int(self.zoom_multiplier), interpolation=cv2.INTER_NEAREST)
        image_array = Image.fromarray(image)
        self.image_tk = ImageTk.PhotoImage(image=image_array)
        self.image_canvas.config(scrollregion=(0,0,image.shape[1],image.shape[0]))
        self.image_canvas.create_image(0, 0, image=self.image_tk, anchor=tk.NW)

    def zoom_out(self):
        self.zoom_multiplier = self.zoom_multiplier - 1.0
        if self.zoom_multiplier == 0.0:
            self.zoom_multiplier = 1.0
        self.show_image()

    def zoom_in(self):
        self.zoom_multiplier = self.zoom_multiplier + 1.0
        self.show_image()

    def menu_shortcut(self, event):
        if self.image_loaded == True:
            if event.keysym == 'z':
                self.zoom_in()
            elif event.keysym == 'Z':
                self.zoom_out()
            elif event.state == 12 and event.keysym == 's':
                self.save_file()
        if event.state == 12 and event.keysym == 'o':
            self.select_file()
        elif event.state == 12 and event.keysym == 'x':
            self.destroy()

    def onconfigure(self, event):
        new_win_width = self.winfo_width()
        new_win_height = self.winfo_height()
        if self.old_win_width != new_win_width or self.old_win_height != new_win_height:
            self.old_win_width = new_win_width
            self.old_win_height = new_win_height
            self.image_canvas.config(width=new_win_width - 180, height=new_win_height - 50)
            self.image_canvas.config(scrollregion=self.image_canvas.bbox("all"))


def main():
    app = myApp()
    app.mainloop()

if __name__ == "__main__":
    main()



    # # Add slide
    # # var4 = tk.IntVar()
    # # gamma_scale = tk.Scale(root, from_=-3, to=3, resolution=0.1, label='gamma', length=200, orient=tk.HORIZONTAL, variable=var4, digits=2, takefocus=True)
    # # gamma_scale.grid(row=4, column=0, sticky=tk.S)
    # # var5 = tk.IntVar()
    # # scale_scale = tk.Scale(root, from_=0, to=1, resolution=0.1, label='scale', length=200, orient=tk.HORIZONTAL, variable=var5, digits=2, takefocus=True)
    # # scale_scale.grid(row=5, column=0, sticky=tk.S)
    # # var6 = tk.IntVar()
    # # offset_scale = tk.Scale(root, from_=-1, to=1, resolution=0.1, label='offset', length=200, orient=tk.HORIZONTAL, variable=var6, digits=2, takefocus=True)
    # # offset_scale.grid(row=6, column=0, sticky=tk.S)
    #
    # # Show window
    # root.mainloop()
