class Selector {

    constructor(editor) {

        const signals = editor.signals;
        const scene = editor.scene;

        this.editor = editor;
        this.signals = signals;

        // signals

        signals.intersectionsDetected.add((intersects) => {

            if (intersects.length > 0) {

                var object = intersects[0].object;

                while (object.parent !== this.editor.scene) {
                    object = object.parent;
                }

                if (object.userData.object !== undefined) {

                    // helper

                    this.select(object.userData.object);

                } else {

                    this.select(object);

                }

            } else {

                this.select(null);

            }

        });

    }

    select(object) {

        if (this.editor.selected === object) return;

        let uuid = null;

        if (object !== null) {

            uuid = object.uuid;

        }

        this.editor.selected = object;
        this.editor.config.setKey('selected', uuid);

        this.signals.objectSelected.dispatch(object);

    }

    deselect() {

        this.select(null);

    }

}

export { Selector };