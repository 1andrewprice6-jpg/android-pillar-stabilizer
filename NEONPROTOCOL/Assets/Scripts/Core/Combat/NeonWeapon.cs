using UnityEngine;
using NeonProtocol.Core.Input;
using NeonProtocol.Core.Systems;
using NeonProtocol.Core.AI;

namespace NeonProtocol.Core.Combat
{
    public class NeonWeapon : MonoBehaviour
    {
        [Header("Weapon Stats")]
        [SerializeField] private float damage = 20f;
        [SerializeField] private float range = 50f;
        [SerializeField] private float fireRate = 0.1f;
        [SerializeField] private int maxAmmo = 30;
        
        [Header("Visuals")]
        [SerializeField] private ParticleSystem muzzleFlash;
        [SerializeField] private GameObject hitEffectPrefab;

        private float _nextFireTime;
        private int _currentAmmo;
        private Transform _camTransform;

        private void Awake()
        {
            _camTransform = Camera.main.transform;
            _currentAmmo = maxAmmo;
        }

        private void Update()
        {
            if (NeonInputHandler.Instance.FireInput && Time.time >= _nextFireTime && _currentAmmo > 0)
            {
                Shoot();
            }
        }

        private void Shoot()
        {
            _nextFireTime = Time.time + fireRate;
            _currentAmmo--;
            
            if (muzzleFlash) muzzleFlash.Play();

            RaycastHit hit;
            if (Physics.Raycast(_camTransform.position, _camTransform.forward, out hit, range))
            {
                // Damage Logic
                if (hit.collider.TryGetComponent(out ZombieController zombie))
                {
                    zombie.TakeDamage(damage);
                }

                // Visual Hit Logic (Use pooling for these in production)
                if (hitEffectPrefab)
                    Instantiate(hitEffectPrefab, hit.point, Quaternion.LookRotation(hit.normal));
            }
        }

        public void Reload()
        {
            _currentAmmo = maxAmmo;
            // IW-style reload logic
        }
    }
}