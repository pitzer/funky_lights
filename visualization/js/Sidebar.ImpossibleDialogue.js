import { UIPanel, UIRow, UIButton, UISpan, UIText, UINumber, UIBreak } from './libs/ui.js';
import { UIOutliner } from './libs/ui.three.js';


function SidebarImpossibleDialogue( editor ) {

	const config = editor.config;
	const strings = editor.strings;
    const signals = editor.signals;
	const container = new UISpan();

    // outliner

    const nodeStates = new WeakMap();

    function buildOption(object, draggable) {

        const option = document.createElement('div');
        option.draggable = draggable;
        option.innerHTML = buildHTML(object);
        option.value = object.id;

        // opener

        if (nodeStates.has(object)) {

            const state = nodeStates.get(object);

            const opener = document.createElement('span');
            opener.classList.add('opener');

            if (object.children.length > 0) {

                opener.classList.add(state ? 'open' : 'closed');

            }

            opener.addEventListener('click', function () {

                nodeStates.set(object, nodeStates.get(object) === false); // toggle
                updateUI();

            });

            option.insertBefore(opener, option.firstChild);

        }

        return option;

    }

    function getMaterialName(material) {

        if (Array.isArray(material)) {

            const array = [];

            for (let i = 0; i < material.length; i++) {

                array.push(material[i].name);

            }

            return array.join(',');

        }

        return material.name;

    }

    function escapeHTML(html) {

        return html
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

    }

    function getObjectType(object) {

        if (object.isScene) return 'Scene';
        if (object.isCamera) return 'Camera';
        if (object.isLight) return 'Light';
        if (object.isMesh) return 'Mesh';
        if (object.isLine) return 'Line';
        if (object.isPoints) return 'Points';

        return 'Object3D';

    }

    function buildHTML(object) {

        let html = `<span class="type ${getObjectType(object)}"></span> ${escapeHTML(object.name)}`;

        if (object.isMesh) {

            const geometry = object.geometry;
            const material = object.material;

            html += ` <span class="type Geometry"></span> ${escapeHTML(geometry.name)}`;
            html += ` <span class="type Material"></span> ${escapeHTML(getMaterialName(material))}`;

        }

        html += getScript(object.uuid);

        return html;

    }

    function getScript(uuid) {

        if (editor.scripts[uuid] !== undefined) {

            return ' <span class="type Script"></span>';

        }

        return '';

    }

    let ignoreObjectSelectedSignal = false;

    const outliner = new UIOutliner(editor);
    outliner.setId('outliner');
    outliner.onChange(function () {

        ignoreObjectSelectedSignal = true;

        editor.selectById(parseInt(outliner.getValue()));

        ignoreObjectSelectedSignal = false;

    });
    outliner.onDblClick(function () {

        editor.focusById(parseInt(outliner.getValue()));

    });
    container.add(outliner);
    container.add(new UIBreak());
    
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
                setTimeout(function () {
                    signals.launchpadButtonReleased.dispatch(button);
                }, 5000);
            });
            row.add(ui_button);
        }
        settings.add(row);
    }

    // Rotation
    const objectRotationRow = new UIRow();
    const objectRotationX = new UINumber().setStep(10).setNudge(0.1).setUnit('°').setWidth('50px').onChange(update);
    const objectRotationY = new UINumber().setStep(10).setNudge(0.1).setUnit('°').setWidth('50px').onChange(update);
    const objectRotationZ = new UINumber().setStep(10).setNudge(0.1).setUnit('°').setWidth('50px').onChange(update);

    objectRotationRow.add(new UIText(strings.getKey('sidebar/object/rotation')).setWidth('90px'));
    objectRotationRow.add(objectRotationX, objectRotationY, objectRotationZ);

    container.add(objectRotationRow);


    //

    function update() {

        const object = editor.selected;

        if (object !== null) {

            const newRotation = new THREE.Euler(objectRotationX.getValue() * THREE.MathUtils.DEG2RAD, objectRotationY.getValue() * THREE.MathUtils.DEG2RAD, objectRotationZ.getValue() * THREE.MathUtils.DEG2RAD);
            if (new THREE.Vector3().setFromEuler(object.rotation).distanceTo(new THREE.Vector3().setFromEuler(newRotation)) >= 0.01) {

                editor.execute(new SetRotationCommand(editor, object, newRotation));

            }
        }

    }

    function updateTransformRows(object) {

        if (object.isLight ||
            (object.isObject3D && object.userData.targetInverse)) {

            objectRotationRow.setDisplay('none');

        } else {

            objectRotationRow.setDisplay('');

        }

    }

    // events

    signals.objectSelected.add(function (object) {

        if (object !== null) {

            container.setDisplay('block');

            updateUI(object);

        } else {

            container.setDisplay('none');

        }

    });

    signals.objectChanged.add(function (object) {

        if (object !== editor.selected) return;

        updateUI(object);

    });

    signals.refreshSidebarObject3D.add(function (object) {

        if (object !== editor.selected) return;

        updateUI(object);

    });

    function updateUI(object) {

        objectRotationX.setValue(object.rotation.x * THREE.MathUtils.RAD2DEG);
        objectRotationY.setValue(object.rotation.y * THREE.MathUtils.RAD2DEG);
        objectRotationZ.setValue(object.rotation.z * THREE.MathUtils.RAD2DEG);

        updateTransformRows(object);

        const camera = editor.camera;
		const scene = editor.scene;

		const options = [];

		options.push( buildOption( camera, false ) );
		options.push( buildOption( scene, false ) );

		( function addObjects( objects, pad ) {

			for ( let i = 0, l = objects.length; i < l; i ++ ) {

				const object = objects[ i ];

				if ( nodeStates.has( object ) === false ) {

					nodeStates.set( object, false );

				}

				const option = buildOption( object, true );
				option.style.paddingLeft = ( pad * 18 ) + 'px';
				options.push( option );

				if ( nodeStates.get( object ) === true ) {

					addObjects( object.children, pad + 1 );

				}

			}

		} )( scene.children, 0 );

		outliner.setOptions( options );

		if ( editor.selected !== null ) {

			outliner.setValue( editor.selected.id );

		}

    }

	return container;
}

export { SidebarImpossibleDialogue };
