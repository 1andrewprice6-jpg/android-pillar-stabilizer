using UnityEngine;
using NeonProtocol.Core.Systems;

namespace NeonProtocol.Core.Graphics.Decals
{
    public class NeonDecal : MonoBehaviour, IPoolable
    {
        [Header("Settings")]
        [SerializeField] private float lifetime = 10f;
        [SerializeField] private float fadeDuration = 2f;
        
        private SpriteRenderer _spriteRenderer;
        private float _spawnTime;
        private bool _isFading = false;

        private void Awake()
        {
            _spriteRenderer = GetComponent<SpriteRenderer>();
        }

        public void OnSpawn()
        {
            _spawnTime = Time.time;
            _isFading = false;
            Color c = _spriteRenderer.color;
            c.a = 1f;
            _spriteRenderer.color = c;
            
            // Random rotation to prevent patterns from looking repetitive
            transform.rotation = Quaternion.Euler(90, 0, Random.Range(0, 360));
            // Slight scale variance
            float randScale = Random.Range(0.8f, 1.2f);
            transform.localScale = new Vector3(randScale, randScale, 1f);
        }

        private void Update()
        {
            float age = Time.time - _spawnTime;

            if (age >= lifetime - fadeDuration && !_isFading)
            {
                _isFading = true;
            }

            if (_isFading)
            {
                float alpha = Mathf.Clamp01((lifetime - age) / fadeDuration);
                Color c = _spriteRenderer.color;
                c.a = alpha;
                _spriteRenderer.color = c;
            }

            if (age >= lifetime)
            {
                gameObject.SetActive(false);
            }
        }

        public void OnDespawn() { }
    }
}