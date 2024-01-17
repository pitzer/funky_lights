import { UITabbedPanel, UISpan } from './libs/ui.js';

import { SidebarLoadConfig } from './Sidebar.LoadConfig.js';
import { SidebarObject } from './Sidebar.Object.js';


function Sidebar( editor ) {

	const strings = editor.strings;

	const container = new UITabbedPanel();
	container.setId( 'sidebar' );

    const scene = new UISpan().add(
        new SidebarLoadConfig(editor),
        new SidebarObject(editor),
	);
    
    container.addTab('scene', strings.getKey('sidebar/scene'), scene );
    container.select( 'scene' );

	return container;

}

export { Sidebar };
