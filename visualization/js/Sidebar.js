import { UITabbedPanel, UISpan } from './libs/ui.js';

import { SidebarImpossibleDialogue } from './Sidebar.ImpossibleDialogue.js';

function Sidebar( editor ) {

	const strings = editor.strings;

	const container = new UITabbedPanel();
	container.setId( 'sidebar' );

    const launchpad = new UISpan().add(
        new SidebarImpossibleDialogue( editor ),
	);
    
    container.addTab('scene', strings.getKey('sidebar/scene'), launchpad );
    container.select( 'scene' );

	return container;

}

export { Sidebar };
