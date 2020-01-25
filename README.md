# SudokuSolver
Tkinter GUI App to solve Sudoku game using pyomo

The Tkinter GUI has:
A Dimension Input Frame that asks for the dimensions of the game.
And a Sudoku Input Frame that lets the user input the starting values for the game

When the user enters the values and presses optimize, the app creates a pyomo model to solve the assignment problem.
When the optimal solution is found, the app inserts the remaining optimal values in the GUI.

Next updates:
Handle unbounded (not enough initial values)/infeasible (initial values prevent feasible assignment) problems.
Separate files for classes to allow readability.
Error handling in general.

