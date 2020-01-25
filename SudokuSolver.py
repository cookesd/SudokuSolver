# -*- coding: utf-8 -*-
"""
Created on Fri Jan 17 08:44:33 2020

@author: dakar
"""

import tkinter as tk
from collections import OrderedDict
import pyomo.environ as pyo
from pyomo.environ import *


class SudokuSolver(object):
    def __init__(self,test=False):
        self.test = test
        self.inputGui = InputGui(self.test)
        self.inputGui.mainloop()
        self.dim_keys = self.inputGui.dim_keys
        
        
class InputGui(tk.Tk):
    def __init__(self,test = False):
        tk.Tk.__init__(self)
        self.test = test
        
        self.dim_keys = ['rows per cell','columns per cell', 'rows of cells', 'columns of cells']
        self.dim = {key:0 for key in self.dim_keys} #placeholder for the problem dimensions (set in dim_enter)
        self.init_vals = None
        self.prob = None
        self.res = None
        self.tk_res = None
        
        self.title('Sudoku Entry Window')
        container = tk.Frame(self)
        container.pack(side='top',fill='both',expand=True)
        
        # Create Frames
        self.frames = {}
        for i,F in enumerate([DimensionInput,SudokuInput]):
            frame = F(container,self)
            self.frames[F] = frame
            frame.grid(row=0,column=0,sticky='ns')
        self.raise_frame(self.frames[DimensionInput])
      
        
    def raise_frame(self,frame):
        for f in self.frames.values():
            if f != frame:
                f.grid_forget()
            else:
                f.grid(row=0,column=0,sticky='ns')
        

        
    def dim_enter(self,dim_dict):
        self.dim = {key:int(val) for key,val in dim_dict.items()}
        self.dim['rows of cells'] = self.dim['columns per cell']
        self.dim['columns of cells'] = self.dim['rows per cell']
        
        self.dim['total'] = self.dim['rows per cell']*self.dim['columns per cell']
        
        self.dim['total cells'] = self.dim['rows of cells'] * self.dim['columns of cells']
        self.dim['total columns'] = self.dim['columns of cells'] * self.dim['columns per cell']
        self.dim['total rows'] = self.dim['rows of cells'] * self.dim['rows per cell']
        self.frames[SudokuInput].make_shell()
        self.raise_frame(self.frames[SudokuInput])
        
        
    def optimize(self):
        self.prob = OptProb(self.dim,self.init_vals)
        self.res,self.tk_res = self.prob.solve()
        self.display_result()
        
    def display_result(self):
        self.frames[SudokuInput].display_result(self.tk_res)
            

class OptProb(object):
        
    def __init__(self,dimensions,init_vals):
        self.dim = dimensions
        self.init_vals = [(loc,val) for loc,val in init_vals.items()]
        self.max_val = self.dim['total']
        
        self.rpc = self.dim['rows per cell']
        self.cpc = self.dim['columns per cell']
        
        
        self.cells = list(range(self.max_val))
        self.poss_values = list(range(1,self.max_val+1))
        self.set_names = ['row','column']
        
        self.sets = {sn:[' '.join([sn,str(pv)]) for pv in self.cells] for sn in self.set_names}
        self.sets['value'] = self.poss_values
        
        self.cell_row_col_dict = self.make_cell_rows_cols()
        
        self.model = pyo.ConcreteModel()
        
        # create decision variables
        self.model.x = pyo.Var(self.sets['row'],self.sets['column'],self.sets['value'],
                               within = Binary)
        
        # fix initial values
        for iv in self.init_vals:
            ind_dict = self.tk_to_pyo_ind(iv)
            loc = {k:int(v) for k,v in zip(['cell','row','col'],iv[0].split(' '))}
            val = iv[1]
            row = ' '.join(['row',str((loc['cell'] // self.rpc)*self.rpc + loc['row'])])
            col = ' '.join(['column',str((loc['cell'] % self.rpc)*self.cpc + loc['col'])])
            self.model.x[row,col,val].fix(1)
            self.model.x[ind_dict['row'],
                         ind_dict['col'],
                         ind_dict['val']].fix(1)
        
        # create objective and constraints
        def obj_rule(model):
            return(sum(model.x[r,c,v] for r in self.sets['row'] for c in self.sets['column'] for v in self.sets['value']))
        self.model.obj = pyo.Objective(rule=obj_rule)
        
        def one_each_value_per_row_rule(model,v,r):
            return(sum(model.x[r,c,v] for c in self.sets['column']) == 1)
        self.model.one_each_value_per_row = pyo.Constraint(self.sets['value'],self.sets['row'],
                                                           rule = one_each_value_per_row_rule)
        
        def one_each_value_per_col_rule(model,v,c):
            return(sum(model.x[r,c,v] for r in self.sets['row']) == 1)
        self.model.one_each_value_per_col = pyo.Constraint(self.sets['value'],self.sets['column'],
                                                           rule = one_each_value_per_col_rule)
        
        def one_each_value_per_cell_rule(model,v,cell):
            
            # row_div = cell // self.rpc
            # col_div = cell // self.cpc
            # cell_rows = [r for r in self.sets['row'] if int(r.split(' ')[1]) // self.rpc == row_div]
            # cell_cols = [c for c in self.sets['column'] if int(c.split(' ')[1]) // self.cpc == col_div]
            
            return(sum(model.x[r,c,v] for r in self.cell_row_col_dict[cell]['rows'] for c in self.cell_row_col_dict[cell]['cols']) == 1)
            # return(sum(model.x[r,c,v] for r in cell_rows for c in cell_cols) == 1)
        self.model.one_each_value_per_cell = pyo.Constraint(self.sets['value'],self.cells,
                                                           rule = one_each_value_per_cell_rule)
        
        def one_value_per_square_rule(model,r,c):
            return(sum(model.x[r,c,v] for v in self.sets['value']) == 1)
        self.model.one_value_per_square = pyo.Constraint(self.sets['row'],self.sets['column'],
                                                         rule = one_value_per_square_rule)
        
    def make_cell_rows_cols(self):
        cell_row_col_dict = {cell:None for cell in self.cells}
        for cell in self.cells:
            c_row = cell // self.rpc
            c_col = cell % self.cpc
            cell_rows = [r for r in self.sets['row'] if int(r.split(' ')[1]) // self.rpc == c_row]
            cell_cols = [c for c in self.sets['column'] if int(c.split(' ')[1]) // self.cpc == c_col]
            cell_row_col_dict[cell] = {'rows':cell_rows,'cols':cell_cols}
        return(cell_row_col_dict)
        
    def pyo_to_tk_ind(self,pyo_ind):
        crcd = self.cell_row_col_dict
        p_row = pyo_ind['row']
        p_col = pyo_ind['col']
        # p_row_num = int(p_row.split(' ')[1])
        # p_col_num = int(pyo_col.split(' ')[1])
        p_val = pyo_ind['val']
        
        
        cell = [c for c in crcd.keys() if p_row in crcd[c]['rows'] and p_col in crcd[c]['cols']]
        row = crcd[cell[0]]['rows'].index(p_row)
        col = crcd[cell[0]]['cols'].index(p_col)
        tk_ind = ' '.join([str(i) for i in [cell[0],row,col]])
        tk_l = [tk_ind,p_val]
        
        # return(tk_ind)
        return(tk_l)
    
    def tk_to_pyo_ind(self,tk_ind):
        loc = {k:int(v) for k,v in zip(['cell','row','col'],tk_ind[0].split(' '))}
        val = tk_ind[1]
        row = ' '.join(['row',str((loc['cell'] // self.rpc)*self.rpc + loc['row'])])
        col = ' '.join(['column',str((loc['cell'] % self.rpc)*self.cpc + loc['col'])])
        pyo_ind = {k:v for k,v in zip(['row','col','val'],[row,col,val])}
        return(pyo_ind)
                     
    def solve(self):
        # do something
        self.solver = pyo.SolverFactory('glpk')
        res = self.solver.solve(self.model)
        self.sol_dict = {}
        self.tk_sol_dict = {}
        
        for r in self.sets['row']:
            for c in self.sets['column']:
                for v in self.sets['value']:
                    if pyo.value(self.model.x[r,c,v] >= 0.5):
                        tk_l = self.pyo_to_tk_ind({'row':r,'col':c,'val':v})
                        self.tk_sol_dict[tk_l[0]] = tk_l[1]
                        self.sol_dict[(int(r.split(' ')[1]),int(c.split(' ')[1]))] = v
        return(res,self.tk_sol_dict)
        
class DimensionInput(tk.Frame):
    def __init__(self,parent,controller):
        tk.Frame.__init__(self,parent)
        self.controller = controller
        
        #Create labels using OrderedDict so can place them in same order everytime
        dim_keys = self.controller.dim_keys
        
        self.dim_dict = OrderedDict((i,
                                     {'text':'How many '+i+':'
                                      ,'val':None}) for i in dim_keys[:2])
        self.labels = OrderedDict((key,tk.Label(self,
                                    text=self.dim_dict[key]['text'])) for key in self.dim_dict)
        
        for i,lab in enumerate(self.labels.values()):
            lab.grid(row = i,column = 0)
            
        self.entries = OrderedDict((key,tk.Entry(self)) for key in self.dim_dict)
        
        for i,ent in enumerate(self.entries.values()):
            ent.insert(index=0,string='3')
            ent.grid(row = i,column = 1)
            
        #The command is to pass the row and column entry values to the controller
        self.entry_button = tk.Button(self,text='Enter',command = lambda: self.controller.dim_enter({key:val.get() for key,val in self.entries.items()}))#[val.get() for val in self.entries.values()]))#.raise_frame(self.controller.frames[SudokuInput]))
        self.entry_button.grid(row = max([ent.grid_info()['row'] for ent in self.entries.values()]) + 1,
                               column = 1) #puts this at the next available row under the entry labels
        
class SudokuInput(tk.Frame):
    def __init__(self,parent,controller):
        tk.Frame.__init__(self,parent)
        self.parent = parent
        self.controller = controller
        self.entries = OrderedDict() #entry widgets for each Sudoku grid square
        self.cells = OrderedDict() #PaneWindow for each Sudoku cell (matrix)
        
        self.button_list = ['Return to Dimensions','Enter','Optimize']
        self.button_commands = [lambda: self.controller.raise_frame(self.controller.frames[DimensionInput]),
                           self.get_init_values,
                           self.controller.optimize]
        self.buttons = {self.button_list[i]:{'command':self.button_commands[i]} for i in range(len(self.button_list))}
        self.dim = None
        self.tk_res = None
        
        
    def make_shell(self):
        '''Makes the cells in the Frame based on the entries the user supplied
        in the Dimension Input widget.
        
        '''
        # remove all current widgets
        if self.dim == self.controller.dim:
            return
        elif self.dim and self.dim != self.controller.dim:
            
            # for ent in self.entries.values():
            #     ent.destroy()
            for button in self.buttons.values():
                button['button'].destroy()
            for cell in self.cells.values():
                cell.destroy()
            self.__init__(self.parent,self.controller)
                
        self.dim = self.controller.dim #gets the problem dimensions
        
        
        
        
        
        for cr,cell_row in enumerate(range(self.dim['rows of cells'])):
            for cc,cell_col in enumerate(range(self.dim['columns of cells'])):
                cell_num = cr*self.dim['columns of cells'] + cc
                cell = tk.PanedWindow(self,borderwidth=5,relief=tk.SUNKEN)
                cell.grid(row = cr,column = cc)
                self.cells[cell_num] = cell
                
                for r,row in enumerate(range(self.dim['rows per cell'])):
                    for c,col in enumerate(range(self.dim['columns per cell'])):
                        loc = ' '.join((str(cell_num),str(r),str(c)))
                        ent = tk.Entry(self.cells[cell_num],width=3)
                        # ent.insert(index=0,string=''.join([str(i) for i in loc]))
                        ent.grid(row = cr*self.dim['rows per cell']+r,
                                 column = cc*self.dim['columns per cell']+c)
                        self.entries[loc] = ent
                        
        if self.controller.test and self.dim['rows of cells'] == 3 and self.dim['columns of cells'] == 3:
            test_vals = {'0 0 0':9,
                         '0 0 2':8,
                         '0 2 0':7,
                         '0 2 2':3,
                         '1 0 1':5,
                         '1 0 2':6,
                         '1 1 0':8,
                         '1 2 0':9,
                         '2 0 2':4,
                         '2 1 2':2,
                         '2 2 2':5,
                         '3 0 2':2,
                         '3 1 0':8,
                         '3 2 0':5,
                         '3 2 1':4,
                         '4 0 2':8,
                         '4 1 0':7,
                         '4 2 1':6,
                         '4 2 2':1,
                         '5 0 0':3,
                         '5 1 2':9,
                         '6 0 0':1,
                         '6 0 1':5,
                         '7 0 1':8,
                         '8 0 1':4,
                         '8 1 0':1,
                         '8 1 2':8,
                         '8 2 0':5,
                         '8 2 1':7,
                         '8 2 2':3}
            for k,v in test_vals.items():
                self.entries[k].insert(index=0,string=str(v))
            
        for i,button in enumerate(self.button_list):
            self.buttons[button]['button'] = tk.Button(self,text = button,
                                             command = self.buttons[button]['command'])
            self.buttons[button]['button'].grid(column = max([ent.grid_info()['column'] for ent in self.entries.values()],default=0) + 1,
                                                row = i)
        self.buttons['Optimize']['button'].configure(state='disabled')

        self.lbl = tk.Label(self,text = 'Enter the initial values. Press enter to continue.')
        self.lbl.grid(row=max([ent.grid_info()['row'] for ent in self.entries.values()])+1,
                      column = 0,columnspan = self.dim['columns of cells']+2)
    def get_init_values(self):
        ready_to_opt = True
        self.init_vals = {}
        for key,val in self.entries.items():
            if val.get().isdigit():
                self.init_vals[key] = int(val.get())
                val.configure(bg='blue')
            elif val.get():
                # self.init_vals[key] = ''
                ready_to_opt = False
                # val.delete(0,len(val.get()))
                val.configure(bg='red',)
                self.lbl.configure(text='Fix values in RED cells before you can optimize.')
            else:
                val.configure(bg='white')
        if ready_to_opt:
            self.lbl.configure(text='If values you entered are correct, press Optimize to solve.')
            self.buttons['Optimize']['button'].configure(state='normal')

                
        self.controller.init_vals = self.init_vals
                

        
    def display_result(self,tk_res):
        self.tk_res = tk_res
        if self.tk_res:
            for ent_ind,val in self.tk_res.items():
                if self.entries[ent_ind].get():
                    pass
                else:
                    self.entries[ent_ind].configure(bg='green')
                    self.entries[ent_ind].insert(index=0,string=val)
            self.lbl.configure(text='The remaining solutions are in GREEN cells.')
        else:
            self.lbl.configure(text='The problem you entered has either no solution or is unbounded.')
        
# if name == __main__:
app = SudokuSolver(test=True) #remove test = True or set to False for your own problem.

        
        
