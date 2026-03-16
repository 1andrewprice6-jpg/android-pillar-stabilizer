using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace NeonProtocol.Core.Input
{
    public class NeonInputHandler : MonoBehaviour
    {
        public static NeonInputHandler Instance;

        [Header("UI References")]
        [SerializeField] private GameObject touchCanvas;
        [SerializeField] private Image crosshair;

        [Header("Input Actions")]
        public InputActionAsset inputActions;
        private InputAction _moveAction;
        private InputAction _lookAction;
        private InputAction _fireAction;
        private InputAction _jumpAction;
        private InputAction _crouchAction;
        private InputAction _sprintAction; // Added sprint action

        public Vector2 MoveInput { get; private set; }
        public Vector2 LookInput { get; private set; }
        public bool FireInput { get; private set; }
        public bool JumpInput { get; private set; }
        public bool CrouchInput { get; private set; }
        public bool SprintInput { get; private set; } // Added sprint property

        private void Awake()
        {
            Instance = this;
            SetupInput();
        }

        private void SetupInput()
        {
            var map = inputActions.FindActionMap("Player");
            _moveAction = map.FindAction("Move");
            _lookAction = map.FindAction("Look");
            _fireAction = map.FindAction("Fire");
            _jumpAction = map.FindAction("Jump");
            _crouchAction = map.FindAction("Crouch");
            _sprintAction = map.FindAction("Sprint");

            _moveAction.Enable();
            _lookAction.Enable();
            _fireAction.Enable();
            _jumpAction.Enable();
            _crouchAction.Enable();
            _sprintAction.Enable();
        }

        private void Update()
        {
            // Auto-detect gamepad vs touch
            bool isGamepad = Gamepad.current != null;
            if (touchCanvas.activeSelf == isGamepad)
                touchCanvas.SetActive(!isGamepad);

            MoveInput = _moveAction.ReadValue<Vector2>();
            LookInput = _lookAction.ReadValue<Vector2>();
            FireInput = _fireAction.IsPressed();
            JumpInput = _jumpAction.WasPressedThisFrame();
            CrouchInput = _crouchAction.WasPressedThisFrame();
            SprintInput = _sprintAction.IsPressed(); // Read sprint
        }
    }
}