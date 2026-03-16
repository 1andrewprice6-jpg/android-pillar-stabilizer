using UnityEngine;
using NeonProtocol.Maps.Spaceland;
using NeonProtocol.Maps.Rave;
using NeonProtocol.Maps.Shaolin;
using NeonProtocol.Maps.Radioactive;
using NeonProtocol.Maps.Beast;

namespace NeonProtocol.Core.Systems
{
    public enum MapTheme { CosmicBreach, SylvanNightmare, MetroDojo, IsotopeAtoll, VoidStation }

    public class QuestManager : MonoBehaviour
    {
        public static QuestManager Instance;

        [Header("Global Settings")]
        [SerializeField] private MapTheme currentMap;
        
        // References to map-specific managers (can be null if not loaded)
        private SpacelandMechanics _spaceland;
        private RaveMechanics _rave;
        private ShaolinMechanics _shaolin;
        private RadioactiveManager _radioactive;
        private BeastMechanics _beast;

        private void Awake()
        {
            Instance = this;
            InitializeMap();
        }

        private void InitializeMap()
        {
            Debug.Log($"Initializing Map: {currentMap}");
            
            // In a real scenario, you might load these additively or find them in the scene.
            // Here we assume the relevant script is on the same GameObject or in the scene.

            switch (currentMap)
            {
                case MapTheme.CosmicBreach:
                    _spaceland = FindObjectOfType<SpacelandMechanics>();
                    if (_spaceland) _spaceland.StartBossSequence();
                    break;
                case MapTheme.SylvanNightmare:
                    _rave = FindObjectOfType<RaveMechanics>();
                    break;
                case MapTheme.MetroDojo:
                    _shaolin = FindObjectOfType<ShaolinMechanics>();
                    break;
                case MapTheme.IsotopeAtoll:
                    _radioactive = FindObjectOfType<RadioactiveManager>();
                    break;
                case MapTheme.VoidStation:
                    _beast = FindObjectOfType<BeastMechanics>();
                    break;
            }
        }
    }
}