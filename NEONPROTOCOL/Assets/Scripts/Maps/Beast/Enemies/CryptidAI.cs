using UnityEngine;
using UnityEngine.AI;
using NeonProtocol.Core.AI;

namespace NeonProtocol.Maps.Beast.Enemies
{
    public class CryptidAI : ZombieController
    {
        [Header("Wall Crawling")]
        [SerializeField] private LayerMask surfaceLayer;
        [SerializeField] private float crawlSpeed = 8f;
        
        private bool _isWallCrawling = false;

        public override void OnSpawn()
        {
            base.OnSpawn();
            // Cryptids are fast
            GetComponent<NavMeshAgent>().speed = crawlSpeed;
        }

        protected void Update()
        {
            // Logic to check if near wall and transition to crawl animation
            CheckForWalls();
        }

        private void CheckForWalls()
        {
            RaycastHit hit;
            if (Physics.Raycast(transform.position, transform.forward, out hit, 2f, surfaceLayer))
            {
                _isWallCrawling = true;
                // Transition to wall animation
            }
            else
            {
                _isWallCrawling = false;
            }
        }
    }
}