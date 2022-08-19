import { UIPanel, UIRow, UIButton, UISpan, UIText } from './libs/ui.js';


function SidebarLaunchpad( editor ) {

	const config = editor.config;
	const strings = editor.strings;
    const signals = editor.signals;
	const container = new UISpan();

	const settings = new UIPanel();
	settings.setBorderTop( '0' );
	settings.setPaddingTop( '20px' );
	container.add( settings );

	// launchpad buttons

    var buttons = [
        ['0x0', '1x0', '2x0', '3x0', '4x0', '5x0', '6x0', '7x0'], 
        ['0x1', '1x1', '2x1', '3x1', '4x1', '5x1', '6x1', '7x1'], 
        ['0x2', '1x2', '2x2', '3x2', '4x2', '5x2', '6x2', '7x2'], 
        ['0x3', '1x3', '2x3', '3x3', '4x3', '5x3', '6x2', '7x3'], 
        ['0x4', '1x4', '2x4', '3x4', '4x4', '5x4', '6x3', '7x4'], 
        ['0x5', '1x5', '2x5', '3x5', '4x5', '5x5', '6x4', '7x5'], 
        ['0x6', '1x6', '2x6', '3x6', '4x6', '5x6', '6x5', '7x6'], 
        ['0x7', '1x7', '2x7', '3x7', '4x7', '5x7', '6x6', '7x7']
    ]; 
    
    for (const button_row of buttons) { 
        const row = new UIRow().setPaddingLeft('5px');
        for (const button of button_row) { 
            const ui_button = new UIButton(button).setMarginLeft('7px');
            ui_button.onClick(function () {
                signals.launchpadButtonPressed.dispatch(button);
            });
            row.add(ui_button);
        }
        settings.add(row);
    }

	return container;
}

export { SidebarLaunchpad };
