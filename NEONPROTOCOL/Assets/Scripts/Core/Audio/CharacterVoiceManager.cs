using UnityEngine;
using System.Collections.Generic;

namespace NeonProtocol.Core.Audio
{
    public enum VoiceLineType { OutOfAmmo, NeedPoints, PointsEarned, RoundStart, PerkPurchase }

    public class CharacterVoiceManager : MonoBehaviour
    {
        public static CharacterVoiceManager Instance;

        [System.Serializable]
        public struct VoiceLine
        {
            public VoiceLineType type;
            public AudioClip[] clips;
        }

        public List<VoiceLine> voiceLines;
        private AudioSource _audioSource;

        private void Awake()
        {
            Instance = this;
            _audioSource = GetComponent<AudioSource>();
        }

        public void PlayLine(VoiceLineType type)
        {
            var lineSet = voiceLines.Find(x => x.type == type);
            if (lineSet.clips != null && lineSet.clips.Length > 0)
            {
                AudioClip clip = lineSet.clips[Random.Range(0, lineSet.clips.Length)];
                _audioSource.PlayOneShot(clip);
            }
        }
    }
}