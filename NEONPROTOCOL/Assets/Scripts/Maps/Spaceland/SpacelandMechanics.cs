using UnityEngine;
using System.Collections;
using System.Collections.Generic;

namespace NeonProtocol.Maps.Spaceland
{
    public class SpacelandMechanics : MonoBehaviour
    {
        [Header("Simon Says UFO")]
        [SerializeField] private List<Renderer> ufoLights; // 4 colors
        [SerializeField] private float sequenceSpeed = 1.0f;
        
        private List<int> _currentSequence = new List<int>();
        private int _playerInputIndex = 0;
        private bool _isAcceptingInput = false;

        public void StartBossSequence()
        {
            _currentSequence.Clear();
            GenerateNextStep();
            StartCoroutine(PlaySequence());
        }

        private void GenerateNextStep()
        {
            _currentSequence.Add(Random.Range(0, ufoLights.Count));
        }

        private IEnumerator PlaySequence()
        {
            _isAcceptingInput = false;
            yield return new WaitForSeconds(1f);

            foreach (int index in _currentSequence)
            {
                // Flash light
                ufoLights[index].material.EnableKeyword("_EMISSION");
                yield return new WaitForSeconds(sequenceSpeed);
                ufoLights[index].material.DisableKeyword("_EMISSION");
                yield return new WaitForSeconds(0.2f);
            }
            
            _isAcceptingInput = true;
            _playerInputIndex = 0;
        }

        public void PlayerInput(int colorIndex)
        {
            if (!_isAcceptingInput) return;

            if (colorIndex == _currentSequence[_playerInputIndex])
            {
                _playerInputIndex++;
                if (_playerInputIndex >= _currentSequence.Count)
                {
                    Debug.Log("Sequence Complete! Next Level.");
                    GenerateNextStep();
                    StartCoroutine(PlaySequence());
                }
            }
            else
            {
                Debug.Log("Failed! Resetting...");
                // Spawn Brute/Slasher or punish player
                StartBossSequence(); 
            }
        }
    }
}