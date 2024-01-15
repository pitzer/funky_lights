import { UIPanel, UIRow, UIButton, UISpan, UIText, UINumber, UIBreak } from './libs/ui.js';
import { UIOutliner } from './libs/ui.three.js';
import { OBJLoader } from '../js/OBJLoader.js';
import { AddObjectCommand } from '../js/commands/AddObjectCommand.js';
import { SetPositionCommand } from '../js/commands/SetPositionCommand.js';
import { SetRotationCommand } from '../js/commands/SetRotationCommand.js';

import * as BufferGeometryUtils from '../js/BufferGeometryUtils.js';

import headConfigData from '../../config/head_config.json' assert { type: 'json' };
import ledConfigData from '../../config/led_config_impossible_dialogue.json' assert { type: 'json' };


function SidebarObjects( editor ) {

	const config = editor.config;
	const strings = editor.strings;
    const signals = editor.signals;
	const container = new UISpan();

    // constants
    const yOffset = 0.55;

    // Create a 3D cube for each LED
    const textureWidth = 128;
    const textureHeight = 128;
    const cubeWidth = 0.03;
    var baseGeometry = new THREE.BoxGeometry(cubeWidth, cubeWidth, cubeWidth);
    var cubes = [];
    var index = 0;
    for (var segment of ledConfigData.led_segments) {
        for (var led_positions of segment.led_positions) {
            var geometry = baseGeometry.clone();
            geometry.applyMatrix4(new THREE.Matrix4().makeTranslation(led_positions[0], led_positions[1], led_positions[2]));
            // Colors are in order of the LED config. The texture is sized to a power of 2 for more efficient processing by the GPU.
            const u = Math.floor(index / textureWidth) / (textureHeight - 1);
            const v = (index % textureWidth) / (textureWidth - 1);
            var uvAttribute = geometry.attributes.uv;
            for (var i = 0; i < uvAttribute.count; i++) {
                // Not sure why v and u are flipped here. I would have expected them the other way around
                uvAttribute.setXY(i, v, u);
            }
            cubes.push(geometry);
            index = index + 1;
        }
    }

    // Merge all geometries into one buffer for fast rendering.
    const mergedGeometry = BufferGeometryUtils.mergeBufferGeometries(cubes, false);
    const size = textureWidth * textureHeight;
    const initialTextureData = new Uint8Array(4 * size);
    for (let i = 0; i < size; i++) {
        const stride = i * 4;
        initialTextureData[stride] = 0;
        initialTextureData[stride + 1] = 0;
        initialTextureData[stride + 2] = 0;
        initialTextureData[stride + 3] = 255;
    }
    const texture = new THREE.DataTexture(initialTextureData, textureWidth, textureHeight);
    texture.needsUpdate = true;
    var material = new THREE.MeshBasicMaterial({ map: texture });

    // Create head objects
    for (var head of headConfigData.heads) {
        const id = head.id;
        const position = head.position;
        const orientation = head.orientation;
        const loader = new OBJLoader();
        loader.load(
            // resource URL
            head.mesh,
            // called when resource is loaded
            function (object) {
                object.name = id;
                object.position.set(position.x, position.y + yOffset, position.z);
                object.rotateY(orientation * THREE.MathUtils.DEG2RAD)
                editor.execute(new AddObjectCommand(editor, object));

                // Add lights as a child
                var lightsObject = new THREE.Mesh(mergedGeometry, material);
                lightsObject.name = 'lights';
                editor.execute(new AddObjectCommand(editor, lightsObject, object, 0));
                editor.select(object);
            },
            // called when loading is in progresses
            function (xhr) {
                console.log((xhr.loaded / xhr.total * 100) + '% loaded');
            },
            // called when loading has errors
            function (error) {
                console.log('An error happened');
                console.log(error);
            }
        );
    }

    // Start listening to websockets for LED updates
    function startWebSocketForLedMessages() {
        var ws = new WebSocket("ws://" + window.location.hostname + ":5678/");
        ws.onmessage = function (event) {
            var json = JSON.parse(event.data);
            for (let i = 0; i < json.length; i++) {
                let texture = json[i];
                const object_id = texture.object_id;
                const data = Uint8Array.from(atob(texture.texture_data), c => c.charCodeAt(0))
                material.map = new THREE.DataTexture(data, textureWidth, textureHeight);
                material.map.needsUpdate = true;
            }
            editor.signals.sceneGraphChanged.dispatch();
        };
        ws.onclose = function (e) {
            console.log('Socket is closed. Reconnect will be attempted in 1 second.', e.reason);
            setTimeout(function () {
                startWebSocketForLedMessages();
            }, 1000);
        };
        ws.onerror = function (err) {
            ws.close();
        };
    }
    startWebSocketForLedMessages();

	return container;
}

export { SidebarObjects };
