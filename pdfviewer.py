from tkinter import*
import fitz
import math

class ShowPdf():

    img_object_li = []

    def pdf_view(self,master,width=1200,height=600,pdf_location=""):

        self.img_object_li.clear()

        self.frame = master #Frame(master,width= width,height= height,bg="white")
        #self.frame.pack()

        scroll_y = Scrollbar(self.frame,orient="vertical")
        scroll_x = Scrollbar(self.frame,orient="horizontal")

        scroll_x.pack(fill="x",side="bottom")
        scroll_y.pack(fill="y",side="right")

        self.text = Text(self.frame,yscrollcommand=scroll_y.set,xscrollcommand= scroll_x.set,width= width,height= height)
        self.text.pack(side="left")

        scroll_x.config(command=self.text.xview)
        scroll_y.config(command=self.text.yview)

        open_pdf = fitz.open(pdf_location)

        for page in open_pdf:                
            pix = page.get_pixmap()
            pix1 = fitz.Pixmap(pix,0) if pix.alpha else pix
            img = pix1.tobytes("ppm")
            timg = PhotoImage(data = img)
            self.img_object_li.append(timg)

        for i in self.img_object_li:
            self.text.image_create(END,image=i)
            self.text.insert(END,"\n\n")

        self.text.configure(state="disabled")


        return self.frame



