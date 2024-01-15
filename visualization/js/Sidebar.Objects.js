import { UIPanel, UIRow, UIButton, UISpan, UIText, UINumber, UIBreak } from './libs/ui.js';
import { UIOutliner } from './libs/ui.three.js';
import { OBJLoader } from '../js/OBJLoader.js';
import { AddObjectCommand } from '../js/commands/AddObjectCommand.js';
import { SetPositionCommand } from '../js/commands/SetPositionCommand.js';
import { SetRotationCommand } from '../js/commands/SetRotationCommand.js';

import * as BufferGeometryUtils from '../js/BufferGeometryUtils.js';

// constants
const yOffset = 0.55;
const textureWidth = 128;
const textureHeight = 128;
const cubeWidth = 0.03;

function SidebarObjects( editor ) {

	const config = editor.config;
	const strings = editor.strings;
    const signals = editor.signals;
	const container = new UISpan();

    const ledObjects = new Map();
    const ledObjectMaterials = new Map();

    const loader = new THREE.FileLoader();

    // Load object config
    loader.load(
        '../../config/head_config.json',

        function (data) {
            let json = JSON.parse(data);
            // Create head objects
            for (var head of json.heads) {
                createObject(head);
            }
        },

        // onProgress callback
        function (xhr) {
            console.log((xhr.loaded / xhr.total * 100) + '% loaded');
        },

        // onError callback
        function (err) {
            console.error(err);
        }
    );

    // Create a 3D object based on the config.
    function createObject(object_config) {
        const object_id = object_config.id;
        const position = object_config.position;
        const orientation = object_config.orientation;
        const led_config = object_config.led_config;
        const obj_loader = new OBJLoader();
        // Load mesh geometry
        obj_loader.load(
            object_config.mesh,
            function (object) {
                object.name = object_id;
                object.position.set(position.x, position.y + yOffset, position.z);
                object.rotateY(orientation * THREE.MathUtils.DEG2RAD)
                editor.execute(new AddObjectCommand(editor, object));

                // Add lights as a child
                createLightsObject(object_id, led_config, object);
            },
            // called when loading is in progresses
            function (xhr) {
                console.log((xhr.loaded / xhr.total * 100) + '% loaded');
            },
            // called when loading has errors
            function (error) {
                console.log(error);
            }
        );
    }

    // Create LED lights object with texture.
    function createLightsObject(object_id, led_config_url, parent_object) {
        const loader = new THREE.FileLoader();
        loader.load(
            led_config_url,

            function (data) {
                let json = JSON.parse(data);
                const mergedGeometry = createBufferGeometriesForLeds(json);
                const material = createMaterialForLeds();
                var lightsObject = new THREE.Mesh(mergedGeometry, material);
                lightsObject.name = 'lights';
                ledObjects.set(object_id, lightsObject);
                ledObjectMaterials.set(object_id, material);
                editor.execute(new AddObjectCommand(editor, lightsObject, parent_object, 0));
                editor.select(parent_object);
            },

            // onProgress callback
            function (xhr) {
                console.log((xhr.loaded / xhr.total * 100) + '% loaded');
            },

            // onError callback
            function (err) {
                console.error(err);
            }
        );
    }

    // Create a 3D cube for each LED and merge into a buffer.
    function createBufferGeometriesForLeds(ledConfig) {
        var baseGeometry = new THREE.BoxGeometry(cubeWidth, cubeWidth, cubeWidth);
        var cubes = [];
        var index = 0;
        for (var segment of ledConfig.led_segments) {
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
        return BufferGeometryUtils.mergeBufferGeometries(cubes, false);
    }
    
    // Create a texture material shared by all LEDs of an object.
    function createMaterialForLeds() {
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
        return new THREE.MeshBasicMaterial({ map: texture });
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
                let material = ledObjectMaterials.get(object_id);
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
