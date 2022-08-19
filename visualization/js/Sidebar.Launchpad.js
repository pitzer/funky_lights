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

	// language

    const row1 = new UIRow().setPaddingLeft('30px');
    
    const button0x0 = new UIButton('');
    button0x0.onClick(function () {
        signals.launchpadButtonPressed.dispatch('0x0');
    });
    row1.add(button0x0);

    const button1x0 = new UIButton('').setMarginLeft('7px')
    button1x0.onClick(function () {
        signals.launchpadButtonPressed.dispatch('1x0');
    });
    row1.add(button1x0);

    const button2x0 = new UIButton('2x0').setMarginLeft('7px')
    button2x0.onClick(function () {
        signals.launchpadButtonPressed.dispatch('2x0');
    });
    row1.add(button2x0);

    settings.add(row1);


	return container;

}

export { SidebarLaunchpad };
