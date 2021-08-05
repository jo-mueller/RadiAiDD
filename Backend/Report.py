# -*- coding: utf-8 -*-
"""
Created on Thu Jun 17 11:25:07 2021

Can create pdf reports for finalized radiations

@author: muellejoh
"""

import os
# import fpdf
import matplotlib.pyplot as plt
import logging
from datetime import datetime
import traceback

# def create_report

class Report:
    def __init__(self, GUI, **kwargs):
        
        self.GUI = GUI
        
        self.dir = kwargs.get('outdir', os.path.join(os.getcwd(), 'Reports'))
        if not os.path.isdir(self.dir):
            os.mkdir(self.dir)
        
        
        self.sample = kwargs.get('name', 'Default_name')
        self.outdir = os.path.join(self.dir, datetime.now().strftime('%y%m%d_%H%M%S_') + self.sample)
        if not os.path.isdir(self.outdir):
            os.mkdir(self.outdir)
        
        # self.report = FPDF()
        # self.report.add_page()
        # self.report.set_font('Arial', 'B', 12)
        
        self.f = None        
        self.GUI.Button_create_report.clicked.connect(self.create_Report)
        
    def save_image(self, widget, fname):
        
        fname = os.path.join(self.outdir, fname)
        widget.canvas.axes.figure.savefig(fname, dpi=150)
        
    
    def create_Report(self, **kwargs):
        
        x_iso = kwargs.get('x_iso', self.GUI.SpotTxt_x.text())
        y_iso = kwargs.get('y_iso', self.GUI.SpotTxt_y.text())
        f_iso = kwargs.get('f_iso', self.GUI.Text_RG_Filename_IsoCenter.toPlainText())
        # x_Trg = kwargs.get('x_Trg', 0)
        # y_Trg = kwargs.get('y_Trg', 0)
        
        f_report = os.path.join(self.outdir, 'report.txt')
        self.f = open(f_report, 'wt')
        
        # =============================================================================
        #       Isocenter stuff
        # =============================================================================
        
        name = 'Isocenter_image.png'
        self.save_image(self.GUI.Display_Isocenter, name)
        lines = []
        lines.append('Isocenter info:\n' +
                     '\tIsocenter coordinates: x, y = ({:s}, {:s}) '.format(x_iso, y_iso))
        lines.append(f'\tImage: {f_iso}')
        lines.append(f'\tSaved screenshot of isocenter-image: {name}')
        [self.f.write(x + '\n') for x in lines]
        
        # =============================================================================
        #         Registration stuff
        # =============================================================================
        
        self.save_image(self.GUI.Display_Moving, 'Plan_image.png')
        self.save_image(self.GUI.Display_Fixed, 'Treatment_image.png')
        
        lines = []
        lines.append('\nRegistration info:')
        lines.append('\tPlan image: {:s}'.format(self.GUI.Label_Moving.text()))
        lines.append('\tRadiography image: {:s}'.format(self.GUI.Label_Fixed.text()))
        
        lines.append('\tTarget coordinates (plan): x, y={:s}'.format(
            self.GUI.table_TrgCoords.item(0, 0).text()))
        lines.append('\tTarget coordinates (radiography): x, y={:s}'.format(
            self.GUI.table_TrgCoords.item(1, 0).text()))
        
        
        # Landmarks
        lines.append('\tList of landmarks:')
        lines.append('\t\tPlan image\tTreatment image')
        i = 0
        while True:
            try:
                print()
                lines.append('\t\t{:s}\t{:s}'.format(
                    self.GUI.CoordsTable.item(i, 0).text(),
                    self.GUI.CoordsTable.item(i, 1).text()))
            except Exception:
                break
            i += 1
            
        lines.append('\tTransformation parameters: {:s}'.format(self.GUI.Label_Trafo_Params.text()))
        [self.f.write(x + '\n') for x in lines]
        
        # =============================================================================
        #         Motor stage stuff
        # =============================================================================
        
        lines = []
        lines.append('\nMotor stage info:')
        lines.append('\tMotor origin (x,y) = ({:s}, {:s})'.format(
            self.GUI.TableTxt_x.text(), self.GUI.TableTxt_y.text()))
        lines.append('\tMotor destination (x,y) = ({:s}, {:s})'.format(
            self.GUI.TableTxt_xCorr.text(), self.GUI.TableTxt_yCorr.text()))
        lines.append('\tLast known motor coordinates: (x,y) = ({:s}, {:s})'.format(
            self.GUI.TablePosX.text(), self.GUI.TablePosY.text()))

        [self.f.write(x + '\n') for x in lines]
        self.f.close()
            
        logging.info('Report created')
        
        
    # def add_Image(DispObj):
    
        
if __name__ =="__main__":
    
    outdir = os.path.join(os.getcwd(), '..', 'Reports')
    if not os.path.isdir(outdir):
        os.mkdir(outdir)
    
    rep = Report('Blubb', outdir=outdir)
    rep.save()
        
    