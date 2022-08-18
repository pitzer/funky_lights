import { UITabbedPanel, UISpan } from './libs/ui.js';

import { SidebarLaunchpad } from './Sidebar.Launchpad.js';

function Sidebar( editor ) {

	const strings = editor.strings;

	const container = new UITabbedPanel();
	container.setId( 'sidebar' );

    const launchpad = new UISpan().add(
        new SidebarLaunchpad( editor ),
	);
    
    container.addTab('scene', strings.getKey('sidebar/scene'), launchpad );
    container.select( 'scene' );

	return container;

}

export { Sidebar };
