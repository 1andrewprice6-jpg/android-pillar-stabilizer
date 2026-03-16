using System.Collections.Generic;
using UnityEngine;

namespace NeonProtocol.Core.Systems
{
    public interface IPoolable
    {
        void OnSpawn();
        void OnDespawn();
    }

    public class NeonPooler : MonoBehaviour
    {
        public static NeonPooler Instance;

        [System.Serializable]
        public struct Pool
        {
            public string tag;
            public GameObject prefab;
            public int size;
        }

        public List<Pool> pools;
        private Dictionary<int, Queue<GameObject>> _poolDict = new Dictionary<int, Queue<GameObject>>();

        void Awake() 
        { 
            Instance = this;
            PrewarmPools();
        }

        private void PrewarmPools()
        {
            foreach (var pool in pools)
            {
                int tagHash = pool.tag.GetHashCode();
                Queue<GameObject> objectPool = new Queue<GameObject>();

                for (int i = 0; i < pool.size; i++)
                {
                    GameObject obj = Instantiate(pool.prefab, transform);
                    obj.SetActive(false);
                    objectPool.Enqueue(obj);
                }
                _poolDict.Add(tagHash, objectPool);
            }
        }

        public GameObject Spawn(string tag, Vector3 pos, Quaternion rot)
        {
            int hash = tag.GetHashCode();
            if (!_poolDict.ContainsKey(hash)) return null;

            GameObject obj = _poolDict[hash].Dequeue();
            
            // Optimization: Set position BEFORE enabling to avoid physics recalculation
            obj.transform.SetPositionAndRotation(pos, rot);
            obj.SetActive(true);

            if (obj.TryGetComponent(out IPoolable poolable)) poolable.OnSpawn();

            _poolDict[hash].Enqueue(obj); // Circular buffer approach
            return obj;
        }
    }
}