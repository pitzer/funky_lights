import * as THREE from 'three';

import { UIPanel, UIRow, UINumber, UISpan, UIText } from './libs/ui.js';


function SidebarHeads(editor) {
    const strings = editor.strings;
    const signals = editor.signals;
    const rotationYValues = new Map();

    const container = new UISpan();

    const panel = new UIPanel();
    panel.setBorderTop('0');
    panel.setPaddingTop('20px');
    container.add(panel);



    signals.addHead.add(function (object_config) {
        const object_id = object_config.id;
        const orientation = object_config.orientation;
        const rotationY = new UINumber().setStep(10).setNudge(0.1).setUnit('°').setWidth('50px');
        rotationY.setValue(orientation);
        rotationYValues.set(object_id, rotationY); 
        const row = new UIRow();
        row.add(new UIText(object_id).setWidth('90px'));
        row.add(rotationY);
        panel.add(row);
    });

    signals.headChanged.add(function (head) {
        var rotationY = rotationYValues.get(head.id);
        if (rotationY !== undefined) {
            rotationY.setValue(head.orientation);
        }
    });

    return container;
}

export { SidebarHeads };