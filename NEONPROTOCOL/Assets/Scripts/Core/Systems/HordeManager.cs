using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using NeonProtocol.Core.Systems;

namespace NeonProtocol.Core.Systems
{
    public class HordeManager : MonoBehaviour
    {
        public static HordeManager Instance;

        [Header("Round Settings")]
        public int currentRound = 1;
        public float HealthMultiplier => 1f + (currentRound * 0.15f);
        public float SpeedMultiplier => Mathf.Min(1.5f, 1f + (currentRound * 0.05f));

        [Header("Spawn Logic")]
        [SerializeField] private Transform[] spawnPoints;
        [SerializeField] private float timeBetweenSpawns = 2f;
        
        private int _zombiesRemainingInRound;
        private int _zombiesActive;
        private bool _isRoundActive;

        private void Awake() => Instance = this;

        private void Start() => StartCoroutine(StartRoundRoutine());

        private IEnumerator StartRoundRoutine()
        {
            yield return new WaitForSeconds(5f); // Intermission
            _isRoundActive = true;
            _zombiesRemainingInRound = 5 + (currentRound * 3);
            
            while (_zombiesRemainingInRound > 0)
            {
                if (_zombiesActive < 24) // IW engine cap for active zombies
                {
                    SpawnZombie();
                    _zombiesRemainingInRound--;
                    yield return new WaitForSeconds(timeBetweenSpawns / SpeedMultiplier);
                }
                yield return null;
            }
        }

        private void SpawnZombie()
        {
            Transform sp = spawnPoints[Random.Range(0, spawnPoints.Length)];
            NeonPooler.Instance.Spawn("Zombie", sp.position, sp.rotation);
            _zombiesActive++;
        }

        public void OnZombieDeath()
        {
            _zombiesActive--;
            if (_zombiesActive <= 0 && _zombiesRemainingInRound <= 0)
            {
                EndRound();
            }
        }

        private void EndRound()
        {
            currentRound++;
            StartCoroutine(StartRoundRoutine());
        }
    }
}