"""
fractal_widgets.py

Copyright (C) 2025 Daniel Brogan

This file is part of the Fractal Cortex project.
Fractal Cortex is a Multidirectional 5-Axis FDM Slicer.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import pyglet
from pyglet import event
from pyglet.window import key
import glooey
from glooey import drawing

"""
Contains all classes that define the structure of the custom widgets that are used to populate the GUI.
"""

""" CUSTOM DECORATION CLASSES """

class Custom_Image(glooey.Frame):
    custom_alignment = "top"

    class Decoration(glooey.Background):
        custom_image = None

    def __init__(self, backgroundImage):
        self.backgroundImage = backgroundImage
        self.Decoration.custom_image = pyglet.image.load(self.backgroundImage)
        super().__init__()

class Light_Gray_Background(glooey.Background):
    custom_color = "#F3F3F3"

class Dark_Gray_Background(glooey.Background):
    custom_color = "#D9D9D9"

class Pop_Up_Box_Label(glooey.Label):
    custom_font_size = 10
    custom_color = "black"
    custom_font_name = "Roboto"
    custom_bold = True
    custom_alignment = "center"

class Title_Label(glooey.Label):
    custom_font_size = 14
    custom_color = "black"
    custom_font_name = "Roboto"
    custom_bold = True
    custom_alignment = "center"

class Widget_Label(glooey.Label):
    custom_font_size = 10
    custom_color = "black"
    custom_font_name = "Roboto"
    custom_bold = False

class Black_Underline_Frame(glooey.Frame):  # This is the background rectangle for the selected option
    class Box(glooey.Bin):
        custom_padding = 0
        custom_width_hint = 450
        custom_height_hint = 1

    class Decoration(glooey.Background):
        custom_color = "black"

class Gray_Underline_Frame(glooey.Frame):  # This is the background rectangle for the selected option
    class Box(glooey.Bin):
        custom_padding = 0
        custom_width_hint = 450
        custom_height_hint = 1

    class Decoration(glooey.Background):
        custom_color = "#B8B8B8"

""" SPIN BOX CLASSES """

class Spin_Box(glooey.Widget):
    custom_alignment = "center"

    def __init__(
        self,
        boxWidth,
        defaultValue,
        minValue,
        maxValue,
        increment,
        dataType,
        updateFunction,
        units,
    ):
        super().__init__()
        self.boxWidth = boxWidth
        self.defaultValue = defaultValue
        self.minValue = minValue
        self.maxValue = maxValue
        self.increment = increment
        self.dataType = dataType
        self.updateFunction = updateFunction
        self.units = units
        self.NANs = ["", "-", ".", "-."]

        self.entryBox = Spin_Box_Entry_Box(
            self.boxWidth, self.defaultValue, self.minValue, self.maxValue, self.units
        )
        self.entryBox.entryBoxEditableLabel.set_width_hint(self.boxWidth - 10)
        self.entryBox.entryBoxEditableLabel.updateFunction = self.updateFunction
        self.entryBox.entryBoxEditableLabel.NANs = self.NANs

        if dataType == "int":
            self.entryBox.entryBoxEditableLabel.dataType = "int"
        else:
            self.entryBox.entryBoxEditableLabel.dataType = "float"

        spinBoxHBox = glooey.HBox(2)
        spinBoxButtonBox = glooey.VBox(2)
        spinBoxHBox.add(self.entryBox, 0)
        spinBoxButtonBox.add(
            Unlabeled_Image_Button(
                "image_resources/spinBox_Images/up/base.png",
                "image_resources/spinBox_Images/up/over.png",
                "image_resources/spinBox_Images/up/down.png",
                self.up,
                [],
            ),
            0,
        )
        spinBoxButtonBox.add(
            Unlabeled_Image_Button(
                "image_resources/spinBox_Images/down/base.png",
                "image_resources/spinBox_Images/down/over.png",
                "image_resources/spinBox_Images/down/down.png",
                self.down,
                [],
            ),
            1,
        )
        spinBoxHBox.add(spinBoxButtonBox, 1)

        self._attach_child(spinBoxHBox)

    def up(self):
        if (
            self.entryBox.entryBoxEditableLabel.get_text() in self.NANs
        ):  # If the user deleted everything in the spinbox, use zero as the currentValue
            currentValue = 0.0
        else:
            currentValue = float(self.entryBox.entryBoxEditableLabel.get_text())
        newValue = currentValue + self.increment
        if newValue > self.maxValue:
            newValue = self.maxValue
        if newValue < self.minValue:
            newValue = self.minValue
        if self.dataType == "int":
            newValue = int(newValue)
        self.entryBox.entryBoxEditableLabel.set_text(str(newValue))
        self.updateFunction()  #

    def down(self):
        if (
            self.entryBox.entryBoxEditableLabel.get_text() in self.NANs
        ):  # If the user deleted everything in the spinbox, use zero as the currentValue
            currentValue = 0.0
        else:
            currentValue = float(self.entryBox.entryBoxEditableLabel.get_text())
        newValue = currentValue - self.increment
        if newValue < self.minValue:
            newValue = self.minValue
        if self.dataType == "int":
            newValue = int(newValue)
        self.entryBox.entryBoxEditableLabel.set_text(str(newValue))
        self.updateFunction()  #

    def update_maxValue(self, newValue):
        self.maxValue = newValue
        self.entryBox.maxValue = newValue
        self.entryBox.entryBoxEditableLabel.maxValue = newValue


class Spin_Box_Entry_Box(glooey.Stack):
    def __init__(self, boxWidth, defaultValue, minValue, maxValue, units):
        super().__init__()
        self.boxWidth = boxWidth
        self.defaultValue = defaultValue
        self.minValue = minValue
        self.maxValue = maxValue
        self.units = units

        self.entryBoxFrame = self.Entry_Box_Frame(self.boxWidth)
        self.entryBoxEditableLabel = Spin_Box_EditableLabel(self.defaultValue)
        self.label = self.Units_Label(self.units)

        self.insert(
            self.entryBoxFrame, 0
        )  # Layer order is specified as the last argument. Higher numbers go in front of lower ones
        self.insert(self.entryBoxEditableLabel, 1)
        self.insert(self.label, 2)

        # Setting entryBox Attributes
        self.entryBoxEditableLabel.defaultValue = self.defaultValue
        self.entryBoxEditableLabel.minValue = self.minValue
        self.entryBoxEditableLabel.maxValue = self.maxValue
        self.entryBoxEditableLabel.set_font_name("Roboto")

        # Setting label Attributes
        self.label.alignment = "right"
        self.label.set_color("gray")
        self.label.set_font_name("Roboto")
        self.label.set_font_size(10)

    class Entry_Box_Frame(glooey.Frame):
        def __init__(self, boxWidth):
            super().__init__()
            self.boxWidth = boxWidth
            self.Box.set_width_hint(self, self.boxWidth)

        class Box(glooey.Bin):
            custom_height_hint = 28

            def __init__(self):
                super().__init__()
                self._child = None

        class Decoration(glooey.Background):
            custom_color = "#F0FFFF"
            custom_outline = "#B8B8B8"

            def on_mouse_enter(self, x, y):
                self.set_color("white")
                self.set_outline("#F0FFFF")
                super().on_mouse_enter(x, y)

            def on_mouse_leave(self, x, y):
                self.set_color("#F0FFFF")
                self.set_outline("#B8B8B8")
                super().on_mouse_leave(x, y)

    class Units_Label(glooey.Label):
        custom_padding = 4


class Spin_Box_EditableLabel(glooey.EditableLabel):
    custom_color = "black"
    custom_selection_color = "gray"
    custom_selection_background_color = "#40E0D0"
    custom_alignment = "left"
    custom_padding = 4

    def __init__(self, text="", line_wrap=None, **style):
        super().__init__(text, line_wrap, **style)
        self.disableSliceButton = False
        self._caret = None
        self._focus = False
        self._is_mouse_over = False
        self._unfocus_on_enter = self.custom_unfocus_on_enter
        self.defaultValue = None
        self.minValue = None
        self.maxValue = None
        self.dataType = None
        self.updateFunction = None
        self.NANs = None
        self._selection_color = self.custom_selection_color
        self._selection_background_color = self.custom_selection_background_color

    def do_make_new_layout(self, document, kwargs):
        # Make a new layout (optimized for editing).
        new_layout = pyglet.text.layout.IncrementalTextLayout(document, **kwargs)

        new_layout.selection_color = drawing.Color.from_anything(
            self._selection_color
        ).tuple
        new_layout.selection_background_color = drawing.Color.from_anything(
            self._selection_background_color or self.color
        ).tuple

        if self._layout:
            new_layout.set_selection(
                self._layout._selection_start,
                self._layout._selection_end,
            )

        # Make a new caret (Use the subclasses Caret here)
        new_caret = Spin_Box_Numeric_Caret(new_layout, color=self.color[:3])
        new_caret.defaultValue = self.defaultValue
        new_caret.minValue = self.minValue
        new_caret.maxValue = self.maxValue
        new_caret.parentWidget = self

        if self._caret:
            new_caret.position = self._caret.position
            new_caret.mark = self._caret.mark

            self.window.remove_handlers(self._caret)
            self._caret.delete()

        # Match the caret's behavior to the widget's current focus state.
        if self._focus:
            new_caret.on_activate()
            self.window.push_handlers(new_caret)
        else:
            new_caret.on_deactivate()

        self._caret = new_caret
        return new_layout

    def do_resize(self):
        try:
            self.unfocus()  # This makes it so that if the caret is in an entry box and the window is resized, it won't restrict the user from selecting another widget
        except:
            pass

    def on_window_mouse_press(self, x, y, button, modifiers):
        # Check if mouse is outside of the label when clicked. If so, call the on_mouse_leave function
        # If I need to troubleshoot this in the future, I can try testing x and y against self.rect
        self.on_mouse_leave(x, y)

        if not self._is_mouse_over:
            self.unfocus()

    def set_text_color(self, color):
        """Set the color of the text in the document."""
        if self._layout and self._layout.document:
            self._layout.document.set_style(
                0, len(self._layout.document.text), {"color": color}
            )

    def on_insert_text(self, start, text):
        self._text = self._layout.document.text
        if self.dataType == "int":
            if self._text not in self.NANs:  # If the current text is a valid number
                self._layout.document.text = str(int(float(self._text)))
        self.dispatch_event("on_edit_text", self)


class Spin_Box_Numeric_Caret(pyglet.text.caret.Caret):
    def __init__(self, layout, batch=None, color=(0, 0, 0)):
        super().__init__(layout, batch=None, color=(0, 0, 0))
        self.defaultValue = None
        self.minValue = None
        self.maxValue = None
        self.parentWidget = None

    def on_text(self, text):
        allowedChars = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "-"]
        if text in allowedChars:  # Only allow numbers or decimal points
            previousText = Entry_Box_EditableLabel.get_text(self)
            if (
                "." in previousText and text == "."
            ):  # Don't allow the user to input more than one decimal point
                pass
            elif (
                "-" in previousText and text == "-"
            ):  # Don't allow the user to input more than one negative sign
                pass
            elif (
                text == "-" and self._position != 0
            ):  # Don't allow the user to input a negative sign anywhere other than index zero
                pass
            else:
                super().on_text(text)
            currentText = Entry_Box_EditableLabel.get_text(self)
            try:
                value = float(
                    currentText
                )  # If this does not convert to a float, that is how to determine if this is a valid number
                if value < self.minValue:
                    self.parentWidget.set_text_color((255, 0, 0, 255))
                    self._layout.document.text = str(self.minValue)  # New
                elif value > self.maxValue:
                    self.parentWidget.set_text_color((255, 0, 0, 255))
                    self._layout.document.text = str(self.maxValue)  # New
                else:  # Number is valid and within acceptable bounds
                    self.parentWidget.set_text_color((0, 0, 0, 255))
            except:  # If number is invalid
                self.parentWidget.set_text_color((255, 0, 0, 255))

        self.parentWidget.updateFunction()  # Every time text is inserted, run the specified update function

    def on_text_motion(self, motion, select=False):
        if motion == key.MOTION_BACKSPACE:
            if self.mark is not None:
                self._delete_selection()
            elif self._position > 0:
                self._position -= 1
                self._layout.document.delete_text(self._position, self._position + 1)
            # Adding this to protect from exceeding min and max limits upon removing a character
            currentText = Entry_Box_EditableLabel.get_text(self)
            if currentText == "":
                pass
            else:
                try:
                    value = float(
                        currentText
                    )  # If this does not convert to a float, that is how to determine if this is a valid number
                    if value < self.minValue:
                        self.parentWidget.set_text_color((255, 0, 0, 255))
                        self._layout.document.text = str(self.minValue)  # New
                    elif value > self.maxValue:
                        self.parentWidget.set_text_color((255, 0, 0, 255))
                        self._layout.document.text = str(self.maxValue)  # New
                    else:  # Number is valid and within acceptable bounds
                        self.parentWidget.set_text_color((0, 0, 0, 255))
                except:  # If number is invalid
                    self.parentWidget.set_text_color((255, 0, 0, 255))
        elif motion == key.MOTION_DELETE:
            if self.mark is not None:
                self._delete_selection()
            elif self._position < len(self._layout.document.text):
                self._layout.document.delete_text(self._position, self._position + 1)
            # Adding this to protect from exceeding min and max limits upon removing a character
            currentText = Entry_Box_EditableLabel.get_text(self)
            if currentText == "":
                pass
            else:
                try:
                    value = float(
                        currentText
                    )  # If this does not convert to a float, that is how to determine if this is a valid number
                    if value < self.minValue:
                        self.parentWidget.set_text_color((255, 0, 0, 255))
                        self._layout.document.text = str(self.minValue)  # New
                    elif value > self.maxValue:
                        self.parentWidget.set_text_color((255, 0, 0, 255))
                        self._layout.document.text = str(self.maxValue)  # New
                    else:  # Number is valid and within acceptable bounds
                        self.parentWidget.set_text_color((0, 0, 0, 255))
                except:  # If number is invalid
                    self.parentWidget.set_text_color((255, 0, 0, 255))
        elif self._mark is not None and not select:
            self._mark = None
            self._layout.set_selection(0, 0)

        if motion == key.MOTION_LEFT:
            self.position = max(0, self.position - 1)
        elif motion == key.MOTION_RIGHT:
            self.position = min(len(self._layout.document.text), self.position + 1)
        elif motion == key.MOTION_UP:
            self.line = max(0, self.line - 1)
        elif motion == key.MOTION_DOWN:
            line = self.line
            if line < self._layout.get_line_count() - 1:
                self.line = line + 1
        elif motion == key.MOTION_BEGINNING_OF_LINE:
            self.position = self._layout.get_position_from_line(self.line)
        elif motion == key.MOTION_END_OF_LINE:
            line = self.line
            if line < self._layout.get_line_count() - 1:
                self._position = self._layout.get_position_from_line(line + 1) - 1
                self._update(line)
            else:
                self.position = len(self._layout.document.text)
        elif motion == key.MOTION_BEGINNING_OF_FILE:
            self.position = 0
        elif motion == key.MOTION_END_OF_FILE:
            self.position = len(self._layout.document.text)
        elif motion == key.MOTION_NEXT_WORD:
            pos = self._position + 1
            m = self._next_word_re.search(self._layout.document.text, pos)
            if not m:
                self.position = len(self._layout.document.text)
            else:
                self.position = m.start()
        elif motion == key.MOTION_PREVIOUS_WORD:
            pos = self._position
            m = self._previous_word_re.search(self._layout.document.text, 0, pos)
            if not m:
                self.position = 0
            else:
                self.position = m.start()

        self._next_attributes.clear()
        self._nudge()

        self.parentWidget.updateFunction()  # Every time the text is deleted or backspaced, run the update function
        return event.EVENT_HANDLED

    def _update(self, line=None, update_ideal_x=True):
        # _mark is the position of the caret

        if line is None:
            line = self._layout.get_line_from_position(self._position)
            self._ideal_line = None
        else:
            self._ideal_line = line
        x, y = self._layout.get_point_from_position(self._position, line)
        if update_ideal_x:
            self._ideal_x = x

        if (
            self._position == 0
        ):  # If the caret is on the left of the first character, translate it to the right by 1 pixel so it becomes visible
            x += 1

        x -= self._layout.top_group.view_x
        y -= self._layout.top_group.view_y
        font = self._layout.document.get_font(max(0, self._position - 1))
        self._list.vertices[:] = [x, y + font.descent, x, y + font.ascent]

        if self._mark is not None:
            self._layout.set_selection(
                min(self._position, self._mark), max(self._position, self._mark)
            )

        self._layout.ensure_line_visible(line)
        self._layout.ensure_x_visible(x)

""" DROP-DOWN MENU CLASS """

class Drop_Down_Menu(glooey.Widget):
    class Selected_Option_Frame(
        glooey.Frame
    ):  # This is the background rectangle for the selected option
        class Box(glooey.Bin):
            custom_padding = 4
            custom_width_hint = 100
            custom_height_hint = 20

        class Decoration(glooey.Background):
            custom_color = "#40E0D0"
            custom_outline = "black"

    class Selected_Option_Label(
        glooey.Label
    ):  # This is the label for the selected option
        custom_alignment = "left"
        custom_color = "black"
        custom_bold = True

    class Highlighted_Option_Frame(
        glooey.Frame
    ):  # This is the background rectangle for the selected option in the drop down list
        class Box(glooey.Bin):
            custom_padding = 4
            custom_width_hint = 100
            custom_height_hint = 20

        class Decoration(glooey.Background):
            custom_color = "66ffff"
            custom_outline = "gray"

            def on_mouse_enter(self, x, y):
                self.set_color("ccfeea")
                self.set_outline("white")
                super().on_mouse_enter(x, y)

            def on_mouse_leave(self, x, y):
                self.set_color("66ffff")
                self.set_outline("gray")
                super().on_mouse_leave(x, y)

    class Additional_Option_Frame(
        glooey.Frame
    ):  # This is the background rectangle for each additional option in the drop down list
        class Box(glooey.Bin):
            custom_padding = 4
            custom_width_hint = 100
            custom_height_hint = 20

        class Decoration(glooey.Background):
            custom_color = "F0FFFF"
            custom_outline = "gray"

            def on_mouse_enter(self, x, y):
                self.set_color("ccfeea")
                self.set_outline("white")
                super().on_mouse_enter(x, y)

            def on_mouse_leave(self, x, y):
                self.set_color("F0FFFF")
                self.set_outline("gray")
                super().on_mouse_leave(x, y)

    class Additional_Option_Label(
        glooey.Label
    ):  # This is the label for each additional option in the drop down list
        custom_alignment = "left"
        custom_color = "black"
        custom_font_name = "Roboto"
        custom_bold = False

    def __init__(self, options, parentStack, stackLevel):
        super().__init__()
        self.options = options  # List of strings. Each string represents an option
        self.parentStack = parentStack  # The stack this drop down menu was added to
        self.stackLevel = stackLevel  # Is the drop down menu above or below the layer of the other drop down menu
        self.opened = (
            False  # Keeps track of whether the drop down menu is opened or not
        )

        self.vbox = glooey.VBox(
            1
        )  # Vertical box that will hold selected option at the top + drop down menu underneath when needed
        self.selectedOption = self.Selected_Option_Frame()  # Frame for selected option
        self.currentSelection = 0  # Name of current selected option
        self.selectedOptionLabel = self.Selected_Option_Label(
            self.options[self.currentSelection]
        )  # Label that displays the current selected option
        self.selectedOption.add(self.selectedOptionLabel)  # Add label on top of frame
        self.vbox.add(
            self.selectedOption
        )  # Add selected option to the first element in the vbox
        self._attach_child(self.vbox)  # Attach the vbox to this widget
        self.counter = 0
        self.additionalOptionFrames = []

    def mouse_is_within_widget(self, x, y, widget):
        widgetLeft = widget.rect.left
        widgetRight = widget.rect.left + widget.rect.width
        widgetBottom = widget.rect.bottom
        widgetTop = widget.rect.bottom + widget.rect.height
        if widgetLeft < x < widgetRight and widgetBottom < y < widgetTop:
            return True
        else:
            return False

    def on_mouse_press(self, x, y, button, modifiers):
        if self.mouse_is_within_widget(
            x, y, self.selectedOption
        ):  # If mouse clicks over selected option, toggle display of options
            if (
                self.stackLevel == "Upper"
            ):  # If the current drop down menu is on a stack layer above an adjacent one, make it so that when the additional options drop down that clicking them does not activate the drop down beneath it. The downside to this is that only two dropdown menus may be placed near each other
                self.parentStack.one_child_gets_mouse = True
            else:
                self.parentStack.one_child_gets_mouse = False
            self.toggle_options()

        for k, frame in enumerate(
            self.additionalOptionFrames
        ):  # If mouse clicks over an additional option, update the selection apropriately and toggle display of options
            if frame.rect is not None:
                if self.mouse_is_within_widget(x, y, frame):
                    self.update_selection(k)
                    self.toggle_options()
                    self.parentStack.one_child_gets_mouse = False  # Make it so that all children in a stack react to mouse clicks

    def toggle_options(self):
        if self.opened == False:  # If the drop down menu is not opened, open it
            self.opened = True
            self.additionalOptionFrames = []
            for option in self.options:
                if (
                    option != self.options[self.currentSelection]
                ):  # If the additional option is not the currently selected option, display normally
                    additionalOption = self.Additional_Option_Frame()
                    optionLabel = self.Additional_Option_Label(option)
                    additionalOption.add(optionLabel)
                    self.additionalOptionFrames.append(additionalOption)
                    self.counter += 1
                    self.vbox.insert(additionalOption, self.counter, size=0)
                elif (
                    option == self.options[self.currentSelection]
                ):  # Else if the additional option is the currently selected option, highlight it
                    highlightedOption = self.Highlighted_Option_Frame()
                    optionLabel = self.Additional_Option_Label(option)
                    highlightedOption.add(optionLabel)
                    self.additionalOptionFrames.append(highlightedOption)
                    self.counter += 1
                    self.vbox.insert(highlightedOption, self.counter, size=0)
            self.counter = 0

        elif self.opened == True:  # If the drop down menu is opened, close it
            self.parentStack.one_child_gets_mouse = (
                False  # Make it so that all children in a stack react to mouse clicks
            )
            self.opened = False
            for frame in self.additionalOptionFrames:
                if frame.parent:
                    self.vbox.remove(frame)

    ##                    self._unfocus()

    def update_selection(
        self, k
    ):  # Update the selected option to whatever was selected
        self.selectedOption.clear()

        self.currentSelection = k
        self.selectedOptionLabel = self.Selected_Option_Label(
            self.options[self.currentSelection]
        )
        self.selectedOption.add(self.selectedOptionLabel)

""" NEWLY REVISED RADIO BUTTON CLASSES """

class Radio_Buttons(glooey.Stack):  # This stack will contain the frame and organizer
    def __init__(
        self,
        orientation,
        isLabeled,
        isUncheckable,
        backgroundImage,
        radioButtonNames,
        radioButtonImages,
        defaultIndex,
        fontSize,
        toggleFunction,
        argsList,
    ):
        super().__init__()
        self.orientation = orientation
        self.isLabeled = isLabeled
        self.isUncheckable = isUncheckable
        self.backgroundImage = backgroundImage
        self.radioButtonNames = radioButtonNames
        self.radioButtonImages = radioButtonImages
        self.defaultIndex = defaultIndex
        self.fontSize = fontSize
        self.toggleFunction = toggleFunction
        self.argsList = argsList
        self.argsList.append(self)
        self.currentlyChecked = None
        self.D_variables = {}
        self.preRendered = False # Applicable to switching view modes. Keeps track if the toolpaths have already been rendered
        self._disabled = False

        self.radioButtonFrame = Radio_Button_Frame(self.backgroundImage)

        if self.orientation == "Horizontal":
            self.organizer = glooey.HBox()
        elif self.orientation == "Vertical":
            self.organizer = glooey.VBox()
        try:
            self.organizer.alignment = "center"
        except:
            print(
                str(self.orientation),
                'is not a valid orientation. Please input either "Horizontal" or "Vertical"',
            )

        self.radioButtons = []
        for k in range(len(radioButtonNames)):
            if self.isLabeled == True:
                radioButton = Labeled_Radio_Button_Stack(
                    self.radioButtons,
                    self,
                    self.radioButtonNames[k],
                    self.radioButtonImages,
                    self.fontSize,
                    self.toggleFunction,
                    self.argsList,
                )
                self.organizer.add(radioButton)
            elif self.isLabeled == False:
                radioButton = Radio_Button(
                    self.radioButtons,
                    self,
                    self.radioButtonNames[k],
                    self.radioButtonImages[k],
                    self,
                    self.toggleFunction,
                    self.argsList,
                )
                self.organizer.add(radioButton)

        self.insert(self.radioButtonFrame, 0)
        self.insert(self.organizer, 1)

        if self.defaultIndex is not None:
            self.radioButtons[
                self.defaultIndex
            ].check()  # Default radio button starts out checked
            self.currentlyChecked = self.radioButtonNames[self.defaultIndex]

        if self.isLabeled == True:
            self.update_radio_button_styles()

    def set_disabled(self, disabled=True):
        """Enable or disable all radio buttons in the group"""
        self._disabled = disabled
        # Propagate disabled state to all radio buttons
        for button in self.radioButtons:
            if self.isLabeled:
                button.radioButton._disabled = disabled
            else:
                button._disabled = disabled

    def update_radio_button_styles(self):
        for button in self.radioButtons:
            button.parentWidget.update_label_style()


class Radio_Button_Frame(glooey.Frame):
    custom_alignment = "center"

    class Decoration(glooey.Background):
        custom_image = None

    def __init__(
        self, backgroundImage
    ):  # orientation, backgroundImage, radioButtonNames, radioButtonImages, defaultIndex, fontSize, toggleFunction, argsList):
        self.backgroundImage = backgroundImage
        self.Decoration.custom_image = pyglet.image.load(self.backgroundImage)
        self.Decoration.custom_alignment = "center"
        super().__init__()


class Labeled_Radio_Button_Stack(glooey.Stack):
    def __init__(
        self,
        group,
        outerStack,
        name,
        radioButtonImages,
        fontSize,
        toggleFunction,
        argsList,
    ):
        super().__init__()
        self.radioButton = Radio_Button(
            group, outerStack, name, radioButtonImages, self, toggleFunction, argsList
        )
        self.label = glooey.Label(name)
        self.fontSize = fontSize
        self.argsList = argsList

        self.insert(
            self.radioButton, 0
        )  # Layer order is specified as the last argument. Higher numbers go in front of lower ones
        self.insert(self.label, 1)

        self.label.alignment = "center"
        self.label.set_color("black")
        self.label.set_font_name("Roboto")
        self.label.set_font_size(self.fontSize)

    def update_label_style(self):
        if self.radioButton.is_checked:
            self.label.set_style(bold=True)
        else:
            self.label.set_style(bold=False)


class Radio_Button(glooey.RadioButton):
    custom_alignment = "center"

    def __init__(
        self,
        group,
        outerStack,
        name,
        radioButtonImages,
        parentWidget,
        toggleFunction,
        argsList,
    ):
        self.radioButtonImages = radioButtonImages
        self.outerStack = outerStack
        self.name = name
        self.parentWidget = parentWidget
        self.toggleFunction = toggleFunction
        self.argsList = argsList
        self._disabled = False

        self.custom_unchecked_base = pyglet.image.load(self.radioButtonImages[0])
        self.custom_unchecked_over = pyglet.image.load(self.radioButtonImages[1])
        self.custom_unchecked_down = pyglet.image.load(self.radioButtonImages[2])

        self.custom_checked_base = pyglet.image.load(self.radioButtonImages[3])
        self.custom_checked_over = pyglet.image.load(self.radioButtonImages[3])
        self.custom_checked_down = pyglet.image.load(self.radioButtonImages[3])

        super().__init__(group)

    def on_click(self, widget):
        if self._defer_clicks_to_proxies and widget is self:
            return
        else:
            if self.is_checked:
                if self.outerStack.isUncheckable == True:
                    self.toggle()
                    self.outerStack.currentlyChecked = "Deactivated"  # Update the variable to the currently selected radio button
                    self.toggleFunction(*self.argsList)
            else:
                self.toggle()
                self.outerStack.currentlyChecked = (
                    self.name
                )  # Update the variable to the currently selected radio button
                self.toggleFunction(*self.argsList)
        if self.outerStack.isLabeled == True:
            self.outerStack.update_radio_button_styles()

    def on_mouse_press(self, x, y, button, modifiers):
        if not self._disabled:
            super().on_mouse_press(x, y, button, modifiers)

    def on_mouse_release(self, x, y, button, modifiers):
        if not self._disabled:
            super().on_mouse_release(x, y, button, modifiers)

    def on_mouse_enter(self, x, y):
        if not self._disabled:
            super().on_mouse_enter(x, y)

    def on_mouse_leave(self, x, y):
        if not self._disabled:
            super().on_mouse_leave(x, y)

""" CHECKBOX CLASS """

class Checkbox(glooey.Checkbox):
    pyglet.resource.path = [".", "image_resources/CheckBox_Images"]
    pyglet.resource.reindex()
    custom_checked_base = pyglet.resource.image("checkedBase.png")
    custom_checked_over = pyglet.resource.image("checkedOver.png")
    custom_checked_down = pyglet.resource.image("checkedDown.png")
    custom_unchecked_base = pyglet.resource.image("uncheckedBase.png")
    custom_unchecked_over = pyglet.resource.image("uncheckedOver.png")
    custom_unchecked_down = pyglet.resource.image("uncheckedDown.png")

    def __init__(self):
        super().__init__()
        self._disabled = False
        
    def set_disabled(self, disabled=True):
        self._disabled = disabled
    
    def on_mouse_press(self, x, y, button, modifiers):
        if not self._disabled:
            super().on_mouse_press(x, y, button, modifiers)

""" BUTTON CLASS """

class Button(glooey.Button):
    def __init__(
        self,
        label,
        fontName,
        fontSize,
        fontColor,
        fontAlignment,
        buttonWidth,
        buttonHeight,
        baseColor,
        overColor,
        downColor,
        function,
        argsList,
    ):
        self.label = label
        self.fontName = fontName
        self.fontSize = fontSize
        self.fontColor = fontColor
        self.fontAlignment = fontAlignment
        self.buttonWidth = buttonWidth
        self.buttonHeight = buttonHeight
        self.baseColor = baseColor
        self.overColor = overColor
        self.downColor = downColor
        self.function = function
        self.argsList = argsList

        self.Foreground.custom_font_name = self.fontName
        self.Foreground.custom_font_size = self.fontSize
        self.Foreground.custom_color = self.fontColor
        self.Foreground.custom_alignment = self.fontAlignment

        self.Base.custom_color = self.baseColor
        self.Base.custom_outline = "white"
        self.Base.custom_width_hint = self.buttonWidth
        self.Base.custom_height_hint = self.buttonHeight

        self.Over.custom_color = self.overColor
        self.Over.custom_outline = "gray"

        self.Down.custom_color = self.downColor
        self.Down.custom_outline = "black"

        super().__init__(self.label)

    def on_click(self, widget):
        self.function(*self.argsList)

    class Foreground(glooey.Label):
        custom_font_name = None
        custom_font_size = None
        custom_color = None
        custom_alignment = None

    class Base(glooey.Background):
        custom_color = None
        custom_outline = None
        custom_width_hint = None
        custom_height_hint = None

    class Over(glooey.Background):
        custom_color = None
        custom_outline = None

    class Down(glooey.Background):
        custom_color = None
        custom_outline = None

""" LABELED IMAGE BUTTON CLASS """

class Labeled_Image_Button(glooey.Button):
    def __init__(
        self,
        label,
        fontName,
        fontSize,
        fontColor,
        fontAlignment,
        baseImage,
        overImage,
        downImage,
        function,
        argsList,
    ):
        self.label = label
        self.fontName = fontName
        self.fontSize = fontSize
        self.fontColor = fontColor
        self.fontAlignment = fontAlignment
        self.baseImage = baseImage
        self.overImage = overImage
        self.downImage = downImage
        self.function = function
        self.argsList = argsList

        self.Foreground.custom_font_name = self.fontName
        self.Foreground.custom_font_size = self.fontSize
        self.Foreground.custom_color = self.fontColor
        self.Foreground.custom_alignment = self.fontAlignment

        self.Base.custom_image = pyglet.image.load(self.baseImage)

        self.Over.custom_image = pyglet.image.load(self.overImage)

        self.Down.custom_image = pyglet.image.load(self.downImage)

        super().__init__(self.label)

    def on_click(self, widget):
        self.function(*self.argsList)

    class Base(glooey.Background):
        custom_image = None

    class Over(glooey.Background):
        custom_image = None

    class Down(glooey.Background):
        custom_image = None

""" UNLABELED IMAGE BUTTON CLASS """

class Unlabeled_Image_Button(glooey.Button):
    def __init__(self, baseImage, overImage, downImage, function, argsList):
        self.baseImage = baseImage
        self.overImage = overImage
        self.downImage = downImage
        self.function = function
        self.argsList = argsList
        self.clearVBOs = False # For the slice button this tracks if toolpaths have been generated

        self.D_variables = {}

        self.sliceFlag = False

        self.Base.custom_image = pyglet.image.load(self.baseImage)

        self.Over.custom_image = pyglet.image.load(self.overImage)

        self.Down.custom_image = pyglet.image.load(self.downImage)

        super().__init__()

    def on_click(self, widget):
        self.function(*self.argsList)

    class Base(glooey.Background):
        custom_image = None

    class Over(glooey.Background):
        custom_image = None

    class Down(glooey.Background):
        custom_image = None

class Disableable_Unlabeled_Image_Button(glooey.Button):
    def __init__(self, baseImage, overImage, downImage, function, argsList, disabledImage=None):
        self.baseImage = baseImage
        self.overImage = overImage
        self.downImage = downImage
        self.disabledImage = disabledImage #or baseImage  # Use baseImage as fallback if no disabledImage
        self.function = function
        self.argsList = argsList
        self.clearVBOs = False # For the slice button this tracks if toolpaths have been generated
        self.D_variables = {}
        self.sliceFlag = False
        self._disabled = False  # Track disabled state
        
        # Load the images
        self.original_base_image = pyglet.image.load(self.baseImage)
        self.Base.custom_image = self.original_base_image
        self.Over.custom_image = pyglet.image.load(self.overImage)
        self.Down.custom_image = pyglet.image.load(self.downImage)
        self.Off.custom_image = pyglet.image.load(self.disabledImage)
        
        super().__init__()
    
    def set_disabled(self, disabled=True):
        """Set the disabled state of the button"""
        if self._disabled != disabled:
            self._disabled = disabled
            if self._disabled == True:
                self._rollover_state = 'off'
                self.disable()
                self.Base.custom_image = self.disabledImage
            else:
                self.enable()
                self.Base.custom_image = self.original_base_image
    
    def on_mouse_press(self, x, y, button, modifiers):
        """Override mouse press to prevent interaction when disabled"""
        if not self._disabled:
            super().on_mouse_press(x, y, button, modifiers)
    
    def on_click(self, widget):
        """Only execute the function if not disabled"""
        if not self._disabled:
            self.function(*self.argsList)
    
    def get_rollover_state(self):
        """Return disabled state when appropriate"""
        if self._disabled:
            return 'disabled'
        return super().get_rollover_state()
    
    class Base(glooey.Background):
        custom_image = None
    
    class Over(glooey.Background):
        custom_image = None
    
    class Down(glooey.Background):
        custom_image = None
    
    class Off(glooey.Background):
        custom_image = None

""" NEWLY REVISED ENTRY BOX CLASSES """

class Entry_Box(glooey.Stack):
    def __init__(self, defaultValue, minValue, maxValue, units):
        super().__init__()
        self.defaultValue = defaultValue
        self.minValue = minValue
        self.maxValue = maxValue
        self.units = units
        self._disabled = False

        self.entryBoxFrame = self.Entry_Box_Frame()
        self.entryBoxEditableLabel = Entry_Box_EditableLabel(self.defaultValue)
        self.label = self.Units_Label(self.units)

        self.insert(
            self.entryBoxFrame, 0
        )  # Layer order is specified as the last argument. Higher numbers go in front of lower ones
        self.insert(self.entryBoxEditableLabel, 1)
        self.insert(self.label, 2)

        # Setting entryBox Attributes
        self.entryBoxEditableLabel.defaultValue = self.defaultValue
        self.entryBoxEditableLabel.minValue = self.minValue
        self.entryBoxEditableLabel.maxValue = self.maxValue
        self.entryBoxEditableLabel.set_font_name("Roboto")

        # Setting label Attributes
        self.label.alignment = "right"
        self.label.set_color("gray")
        self.label.set_font_name("Roboto")
        self.label.set_font_size(10)

    def set_disabled(self, disabled=True):
        """Enable or disable the entry box"""
        self._disabled = disabled
        if disabled:
            self.entryBoxFrame.decoration.set_color("#E0E0E0")  # Gray background
            self.entryBoxFrame.decoration.set_outline("#D0D0D0")  # Lighter outline
            self.entryBoxEditableLabel.set_text_color((128, 128, 128, 255))  # Gray text
            self.entryBoxEditableLabel._disabled = True
        else:
            self.entryBoxFrame.decoration.set_color("#F0FFFF")  # Original background
            self.entryBoxFrame.decoration.set_outline("#B8B8B8")  # Original outline
            self.entryBoxEditableLabel.set_text_color((0, 0, 0, 255))  # Black text
            self.entryBoxEditableLabel._disabled = False

    class Entry_Box_Frame(glooey.Frame):
        def __init__(self):
            super().__init__()

        class Box(glooey.Bin):
            custom_width_hint = 100
            custom_height_hint = 28

        class Decoration(glooey.Background):
            custom_color = "#F0FFFF"
            custom_outline = "#B8B8B8"

            def on_mouse_enter(self, x, y):
                if not self.parent.parent._disabled:  # Only change color if not disabled
                    self.set_color("white")
                    self.set_outline("#F0FFFF")
                    super().on_mouse_enter(x, y)

            def on_mouse_leave(self, x, y):
                if not self.parent.parent._disabled:  # Only change color if not disabled
                    self.set_color("#F0FFFF")
                    self.set_outline("#B8B8B8")
                    super().on_mouse_leave(x, y)

    class Units_Label(glooey.Label):
        custom_padding = 4


class Entry_Box_EditableLabel(glooey.EditableLabel):
    custom_color = "black"
    custom_selection_color = "gray"
    custom_selection_background_color = "#40E0D0"
    custom_alignment = "left"
    custom_width_hint = 90
    custom_padding = 4

    def __init__(self, text="", line_wrap=None, **style):
        super().__init__(text, line_wrap, **style)
        self.disableSliceButton = False
        self._caret = None
        self._focus = False
        self._is_mouse_over = False
        self._unfocus_on_enter = self.custom_unfocus_on_enter
        self.defaultValue = None
        self.minValue = None
        self.maxValue = None
        self._selection_color = self.custom_selection_color
        self._selection_background_color = self.custom_selection_background_color
        self._disabled = False

    def do_make_new_layout(self, document, kwargs):
        # Make a new layout (optimized for editing).
        new_layout = pyglet.text.layout.IncrementalTextLayout(document, **kwargs)

        new_layout.selection_color = drawing.Color.from_anything(
            self._selection_color
        ).tuple
        new_layout.selection_background_color = drawing.Color.from_anything(
            self._selection_background_color or self.color
        ).tuple

        if self._layout:
            new_layout.set_selection(
                self._layout._selection_start,
                self._layout._selection_end,
            )

        # Make a new caret (Use the subclasses Caret here)
        new_caret = Numeric_Caret(new_layout, color=self.color[:3])
        new_caret.defaultValue = self.defaultValue
        new_caret.minValue = self.minValue
        new_caret.maxValue = self.maxValue
        new_caret.parentWidget = self

        if self._caret:
            new_caret.position = self._caret.position
            new_caret.mark = self._caret.mark

            self.window.remove_handlers(self._caret)
            self._caret.delete()

        # Match the caret's behavior to the widget's current focus state.
        if self._focus:
            new_caret.on_activate()
            self.window.push_handlers(new_caret)
        else:
            new_caret.on_deactivate()

        self._caret = new_caret
        return new_layout

    def do_resize(self):
        try:
            self.unfocus()  # This makes it so that if the caret is in an entry box and the window is resized, it won't restrict the user from selecting another widget
        except:
            pass

    def on_window_mouse_press(self, x, y, button, modifiers):
        # Check if mouse is outside of the label when clicked. If so, call the on_mouse_leave function
        # If I need to troubleshoot this in the future, I can try testing x and y against self.rect
        self.on_mouse_leave(x, y)

        if not self._is_mouse_over:
            self.unfocus()

    def set_text_color(self, color):
        """Set the color of the text in the document."""
        if self._layout and self._layout.document:
            self._layout.document.set_style(
                0, len(self._layout.document.text), {"color": color}
            )

    def on_mouse_press(self, x, y, button, modifiers):
        if not self._disabled:
            super().on_mouse_press(x, y, button, modifiers)

    def on_text(self, text):
        if not self._disabled:
            super().on_text(text)

    def on_text_motion(self, motion, select=False):
        if not self._disabled:
            super().on_text_motion(motion, select)

class Numeric_Caret(pyglet.text.caret.Caret):
    def __init__(self, layout, batch=None, color=(0, 0, 0)):
        super().__init__(layout, batch=None, color=(0, 0, 0))
        self.defaultValue = None
        self.minValue = None
        self.maxValue = None
        self.parentWidget = None

    def on_text(self, text):
        allowedChars = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "-"]
        if text in allowedChars:  # Only allow numbers or decimal points
            previousText = Entry_Box_EditableLabel.get_text(self)
            if (
                "." in previousText and text == "."
            ):  # Don't allow the user to input more than one decimal point
                pass
            elif (
                "-" in previousText and text == "-"
            ):  # Don't allow the user to input more than one negative sign
                pass
            elif (
                text == "-" and self._position != 0
            ):  # Don't allow the user to input a negative sign anywhere other than index zero
                pass
            else:
                super().on_text(text)
            currentText = Entry_Box_EditableLabel.get_text(self)
            try:
                value = float(
                    currentText
                )  # If this does not convert to a float, that is how to determine if this is a valid number
                if value < self.minValue:
                    self.parentWidget.set_text_color((255, 0, 0, 255))
                    self.parentWidget.disableSliceButton = True
                elif value > self.maxValue:
                    self.parentWidget.set_text_color((255, 0, 0, 255))
                    self.parentWidget.disableSliceButton = True
                else:  # Number is valid and within acceptable bounds
                    self.parentWidget.set_text_color((0, 0, 0, 255))
                    self.parentWidget.disableSliceButton = False
            except:  # If number is invalid
                self.parentWidget.set_text_color((255, 0, 0, 255))
                self.parentWidget.disableSliceButton = True

    def on_text_motion(self, motion, select=False):
        if motion == key.MOTION_BACKSPACE:
            if self.mark is not None:
                self._delete_selection()
            elif self._position > 0:
                self._position -= 1
                self._layout.document.delete_text(self._position, self._position + 1)
            # Adding this to protect from exceeding min and max limits upon removing a character
            currentText = Entry_Box_EditableLabel.get_text(self)
            if currentText == "":
                pass
            else:
                try:
                    value = float(
                        currentText
                    )  # If this does not convert to a float, that is how to determine if this is a valid number
                    if value < self.minValue:
                        self.parentWidget.set_text_color((255, 0, 0, 255))
                        self.parentWidget.disableSliceButton = True
                    elif value > self.maxValue:
                        self.parentWidget.set_text_color((255, 0, 0, 255))
                        self.parentWidget.disableSliceButton = True
                    else:  # Number is valid and within acceptable bounds
                        self.parentWidget.set_text_color((0, 0, 0, 255))
                        self.parentWidget.disableSliceButton = False
                except:  # If number is invalid
                    self.parentWidget.set_text_color((255, 0, 0, 255))
                    self.parentWidget.disableSliceButton = True
        elif motion == key.MOTION_DELETE:
            if self.mark is not None:
                self._delete_selection()
            elif self._position < len(self._layout.document.text):
                self._layout.document.delete_text(self._position, self._position + 1)
            # Adding this to protect from exceeding min and max limits upon removing a character
            currentText = Entry_Box_EditableLabel.get_text(self)
            if currentText == "":
                pass
            else:
                try:
                    value = float(
                        currentText
                    )  # If this does not convert to a float, that is how to determine if this is a valid number
                    if value < self.minValue:
                        self.parentWidget.set_text_color((255, 0, 0, 255))
                        self.parentWidget.disableSliceButton = True
                    elif value > self.maxValue:
                        self.parentWidget.set_text_color((255, 0, 0, 255))
                        self.parentWidget.disableSliceButton = True
                    else:  # Number is valid and within acceptable bounds
                        self.parentWidget.set_text_color((0, 0, 0, 255))
                        self.parentWidget.disableSliceButton = False
                except:  # If number is invalid
                    self.parentWidget.set_text_color((255, 0, 0, 255))
                    self.parentWidget.disableSliceButton = True
        elif self._mark is not None and not select:
            self._mark = None
            self._layout.set_selection(0, 0)

        if motion == key.MOTION_LEFT:
            self.position = max(0, self.position - 1)
        elif motion == key.MOTION_RIGHT:
            self.position = min(len(self._layout.document.text), self.position + 1)
        elif motion == key.MOTION_UP:
            self.line = max(0, self.line - 1)
        elif motion == key.MOTION_DOWN:
            line = self.line
            if line < self._layout.get_line_count() - 1:
                self.line = line + 1
        elif motion == key.MOTION_BEGINNING_OF_LINE:
            self.position = self._layout.get_position_from_line(self.line)
        elif motion == key.MOTION_END_OF_LINE:
            line = self.line
            if line < self._layout.get_line_count() - 1:
                self._position = self._layout.get_position_from_line(line + 1) - 1
                self._update(line)
            else:
                self.position = len(self._layout.document.text)
        elif motion == key.MOTION_BEGINNING_OF_FILE:
            self.position = 0
        elif motion == key.MOTION_END_OF_FILE:
            self.position = len(self._layout.document.text)
        elif motion == key.MOTION_NEXT_WORD:
            pos = self._position + 1
            m = self._next_word_re.search(self._layout.document.text, pos)
            if not m:
                self.position = len(self._layout.document.text)
            else:
                self.position = m.start()
        elif motion == key.MOTION_PREVIOUS_WORD:
            pos = self._position
            m = self._previous_word_re.search(self._layout.document.text, 0, pos)
            if not m:
                self.position = 0
            else:
                self.position = m.start()

        self._next_attributes.clear()
        self._nudge()
        return event.EVENT_HANDLED

    def _update(self, line=None, update_ideal_x=True):
        # _mark is the position of the caret

        if line is None:
            line = self._layout.get_line_from_position(self._position)
            self._ideal_line = None
        else:
            self._ideal_line = line
        x, y = self._layout.get_point_from_position(self._position, line)
        if update_ideal_x:
            self._ideal_x = x

        if (
            self._position == 0
        ):  # If the caret is on the left of the first character, translate it to the right by 1 pixel so it becomes visible
            x += 1

        x -= self._layout.top_group.view_x
        y -= self._layout.top_group.view_y
        font = self._layout.document.get_font(max(0, self._position - 1))
        self._list.vertices[:] = [x, y + font.descent, x, y + font.ascent]

        if self._mark is not None:
            self._layout.set_selection(
                min(self._position, self._mark), max(self._position, self._mark)
            )

        self._layout.ensure_line_visible(line)
        self._layout.ensure_x_visible(x)
