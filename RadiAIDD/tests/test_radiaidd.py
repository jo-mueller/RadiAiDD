# -*- coding: utf-8 -*-
"""
Created on Fri Nov 26 20:45:18 2021

@author: johan
"""

import RadiAIDD

def test_windows(qtbot):
    main_window = RadiAIDD.radiaidd.MainWindow()
    assert main_window is not None

    isocenter_window = RadiAIDD.Backend.Children.IsoCenter_Child(main_window, None)
    assert isocenter_window is not None

def test_run(qtbot):
    RadiAIDD.run()


# if __name__ == "__main__":
#     test_radiaidd()
