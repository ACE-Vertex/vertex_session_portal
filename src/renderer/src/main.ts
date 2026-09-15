import './shared/tokens.css'
import {
  portalControl
} from './control/control-channel'
import './components/MainFrame/MainFrame'

/**
 * Dedicated UI Control Channel.
 *
 * Vera/Agent UI guidance arrives here through the secure preload bridge.
 * It is deliberately separate from visible conversation text.
 */
window.vertexPortal.onControlCommand(
  (serializedCommand) => {
    portalControl.dispatchSerialized(
      serializedCommand
    )
  }
)
