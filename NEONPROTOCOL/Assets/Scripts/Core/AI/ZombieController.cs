using UnityEngine;
using UnityEngine.AI;
using NeonProtocol.Core.Systems;

namespace NeonProtocol.Core.AI
{
    public enum ZombieState { Spawning, Chasing, Attacking, Dying }

    [RequireComponent(typeof(NavMeshAgent))]
    public class ZombieController : MonoBehaviour, IPoolable
    {
        [Header("Stats")]
        [SerializeField] private float baseHealth = 100f;
        [SerializeField] private float damage = 25f;
        [SerializeField] private float attackRange = 1.5f;
        [SerializeField] private float attackCooldown = 1.5f;

        private NavMeshAgent _agent;
        private Transform _player;
        private ZombieState _state;
        private float _currentHealth;
        private float _nextAttackTime;
        private int _tickOffset;

        private void Awake()
        {
            _agent = GetComponent<NavMeshAgent>();
            _player = GameObject.FindGameObjectWithTag("Player")?.transform;
            // Spread out AI updates across frames to maintain 60FPS
            _tickOffset = Random.Range(0, 10);
        }

        public void OnSpawn()
        {
            _currentHealth = baseHealth * HordeManager.Instance.HealthMultiplier;
            _agent.speed = 3.5f * HordeManager.Instance.SpeedMultiplier;
            _state = ZombieState.Chasing;
            _agent.enabled = true;
        }

        public void OnDespawn()
        {
            _agent.enabled = false;
        }

        private void Update()
        {
            if (_state == ZombieState.Dying || _player == null) return;

            // Optimization: Only update pathfinding every 10 frames
            if ((Time.frameCount + _tickOffset) % 10 == 0)
            {
                _agent.SetDestination(_player.position);
            }

            float dist = Vector3.Distance(transform.position, _player.position);
            if (dist <= attackRange && Time.time >= _nextAttackTime)
            {
                Attack();
            }
        }

        private void Attack()
        {
            _nextAttackTime = Time.time + attackCooldown;
            // Send damage to player
            Debug.Log("Zombie Attacked!");
        }

        public void TakeDamage(float amount)
        {
            _currentHealth -= amount;
            // Logic for points per hit
            Economy.PointsSystem.Instance.AddPoints(10);

            if (_currentHealth <= 0) Die();
        }

        private void Die()
        {
            _state = ZombieState.Dying;
            Economy.PointsSystem.Instance.AddPoints(60); // Kill reward
            gameObject.SetActive(false);
        }
    }
}