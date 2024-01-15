import { UITabbedPanel, UISpan } from './libs/ui.js';

import { SidebarImpossibleDialogue } from './Sidebar.ImpossibleDialogue.js';
import { SidebarObjects } from './Sidebar.Objects.js';

function Sidebar( editor ) {

	const strings = editor.strings;

	const container = new UITabbedPanel();
	container.setId( 'sidebar' );

    const scene = new UISpan().add(
        new SidebarImpossibleDialogue( editor ),
        new SidebarObjects(editor),
	);
    
    container.addTab('scene', strings.getKey('sidebar/scene'), scene );
    container.select( 'scene' );

	return container;

}

export { Sidebar };
